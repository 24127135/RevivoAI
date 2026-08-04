import docker
from docker.errors import DockerException, APIError
import tarfile
import io
import time
import uuid
import concurrent.futures
import posixpath


class DockerSandboxManager:
    def __init__(self):
        try:
            self._client = docker.from_env()
        except DockerException as e:
            raise RuntimeError(f"Cannot connect to Docker Daemon: {e}")

        self._container_id = None
        self._image_name = "python:3.10-slim"
        self._volume_mounts = []
        self._max_iterations = 3
        self._timeout_seconds = 30

        self._memory_limit_mb = 4096
        self._cpu_quota = 100000
        self._cpu_period = 100000

        self._run_as_non_root = True
        self._container = None
        self._WORKSPACE_ROOT = "/workspace"

    def mountVolume(self, hostPath: str, containerPath: str, readOnly: bool = True) -> None:
        """
        Registers a secure volume mount. Must be called prior to createSandbox().
        """
        mode = 'ro' if readOnly else 'rw'
        self._volume_mounts.append(f"{hostPath}:{containerPath}:{mode}")

    def createSandbox(self, image: str = "python:3.10-slim") -> str:
        """
        Initializes an ephemeral container. This container is intended to live only for
        a single execution cycle (create -> inject -> run -> destroy).
        """
        self._image_name = image
        try:
            mem_limit_str = f"{self._memory_limit_mb}m"

            # Start the background sleeper process as root so we can configure permissions.
            # (The untrusted code in runScript will still securely execute as user 1000).
            self._container = self._client.containers.run(
                image=self._image_name,
                command="/bin/sh -c 'while true; do sleep 3600; done'",
                detach=True,
                mem_limit=mem_limit_str,
                cpu_quota=self._cpu_quota,
                cpu_period=self._cpu_period,
                user="root",  # <--- Start container daemon as root
                network_mode="none",
                working_dir=self._WORKSPACE_ROOT,
                volumes=self._volume_mounts if self._volume_mounts else None
            )
            self._container_id = self._container.id

            # One-time root init: prepare a workspace directory owned by the
            # non-root user so per-file mkdir calls in injectCode() never need root.
            if self._run_as_non_root:
                self._container.exec_run(f"mkdir -p {self._WORKSPACE_ROOT}", user="root")
                self._container.exec_run(f"chown -R 1000:1000 {self._WORKSPACE_ROOT}", user="root")

            return self._container_id
        except APIError as e:
            print(f"[Sandbox Error] Cannot create container: {e}")
            return ""

    def _validate_container_path(self, containerPath: str) -> str:
        """
        Mirrors the role of MCPClient.validatePath() but scoped to the sandbox
        filesystem: ensures containerPath resolves strictly inside the bounded
        workspace root, rejecting '..' traversal and absolute escapes, and
        returns the normalized absolute path to use for tar/mkdir.
        Sanitizes absolute Windows host paths down to valid Linux basenames.
        """
        if not containerPath or not containerPath.strip():
            raise ValueError("containerPath must not be empty.")

        # Sanitize absolute Windows paths leaked from the host
        containerPath = containerPath.replace('\\', '/')
        if ":" in containerPath:
            containerPath = containerPath.split("/")[-1]

        candidate = (
            containerPath
            if containerPath.startswith("/")
            else posixpath.join(self._WORKSPACE_ROOT, containerPath)
        )
        normalized = posixpath.normpath(candidate)

        if normalized == self._WORKSPACE_ROOT or not normalized.startswith(self._WORKSPACE_ROOT + "/"):
            raise PermissionError(
                f"Path '{containerPath}' resolves outside the sandbox workspace "
                f"root '{self._WORKSPACE_ROOT}'; refusing to write."
            )

        return normalized

    def injectCode(self, containerPath: str, content: str) -> None:
        """
        Bypasses circular dependency by pushing the candidate code directly into the
        ephemeral container's isolated filesystem via a tarball stream.

        containerPath is validated against the sandbox workspace root before any
        filesystem operation is attempted (see _validate_container_path).
        """
        if not self._container:
            raise RuntimeError("Sandbox has not been initialized.")

        safe_path = self._validate_container_path(containerPath)

        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            content_bytes = content.encode('utf-8')
            tarinfo = tarfile.TarInfo(name=safe_path.split('/')[-1])
            tarinfo.size = len(content_bytes)
            if self._run_as_non_root:
                tarinfo.uid = 1000
                tarinfo.gid = 1000
            tar.addfile(tarinfo, io.BytesIO(content_bytes))

        tar_stream.seek(0)
        dir_path = "/".join(safe_path.split('/')[:-1]) or "/"
        user_conf = "1000:1000" if self._run_as_non_root else "root"
        
        # Verify directory creation
        exit_code, output = self._container.exec_run(f"mkdir -p {dir_path}", user=user_conf)
        if exit_code != 0:
            print(f"[Sandbox Warning] Failed to create directory {dir_path}: {output.decode('utf-8')}")

        self._container.put_archive(dir_path, tar_stream)

    def runScript(self, scriptPath: str, timeout_sec: int = 30) -> dict:
        """
        Executes the injected script asynchronously to prevent event loop blocking.
        Enforces a hard kill on timeout (NFR-PERF-02).

        CRITICAL LIFECYCLE WARNING:
        If this method returns a 'TIMEOUT' status, the underlying container has been
        forcefully killed (SIGKILL) to prevent orphaned processes. The container is
        now dead. The caller MUST run destroySandbox() followed by createSandbox()
        before attempting to inject or run any subsequent code.
        """
        if not self._container:
            return self._build_execution_log("FAILURE", -1, "", "Container not running", 0.0)

        start_time = time.time()
        
        # Ensure we execute using the sanitized path
        safe_script_path = self._validate_container_path(scriptPath)
        cmd = ["python3", safe_script_path]
        user_conf = "1000:1000" if self._run_as_non_root else "root"

        try:
            exec_instance = self._container.client.api.exec_create(
                self._container.id,
                cmd=cmd,
                user=user_conf,
                workdir="/workspace",
            )
            exec_id = exec_instance['Id']

            def _execute_blocking():
                return self._container.client.api.exec_start(exec_id, demux=True)

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(_execute_blocking)

            try:
                output_tuple = future.result(timeout=timeout_sec)

                inspect_data = self._container.client.api.exec_inspect(exec_id)
                exit_code = inspect_data['ExitCode']

                stdout_bytes, stderr_bytes = output_tuple
                stdout_data = stdout_bytes.decode('utf-8') if stdout_bytes else ""
                stderr_data = stderr_bytes.decode('utf-8') if stderr_bytes else ""

                status = "SUCCESS" if exit_code == 0 else "FAILURE"

                return self._build_execution_log(
                    status=status,
                    exit_code=exit_code,
                    stdout=stdout_data,
                    stderr="" if status == "SUCCESS" else stderr_data,
                    duration=(time.time() - start_time) * 1000
                )

            except concurrent.futures.TimeoutError:
                self._container.kill()

                return self._build_execution_log(
                    status="TIMEOUT",
                    exit_code=None,
                    stdout="",
                    stderr="System Error: Container execution terminated. SIGKILL (9) sent due to exceeding timeout threshold.",
                    duration=(time.time() - start_time) * 1000
                )
            finally:
                executor.shutdown(wait=False)

        except Exception as e:
            return self._build_execution_log("FAILURE", -1, "", str(e), (time.time() - start_time) * 1000)

    def _build_execution_log(self, status: str, exit_code, stdout: str, stderr: str, duration: float) -> dict:
        """
        Internal formatter to standardize output into the Execution_log schema payload.
        """
        return {
            "execution_id": str(uuid.uuid4()),
            "patch_id": None,
            "status": status,
            "exit_code": exit_code,
            "stdout_buffer": stdout,
            "stderr_traceback": stderr,
            "execution_time_ms": round(duration, 2)
        }

    def destroySandbox(self) -> None:
        """
        Destroys the ephemeral container and purges all isolated resources.
        """
        if self._container:
            try:
                self._container.remove(force=True)
            except APIError:
                pass
            finally:
                self._container = None
                self._container_id = None
                self._volume_mounts = []