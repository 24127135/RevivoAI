import os
from pathlib import Path


class MCPClient:
    def __init__(self, allowed_root_path: str):
        self.root_path = Path(allowed_root_path).resolve()

        if not self.root_path.exists() or not self.root_path.is_dir():
            raise ValueError(f"Root path {self.root_path} không tồn tại hoặc không phải là thư mục.")

        self._connected = False

    def _validatePath(self, filepath: str) -> Path:

        target_path = Path(filepath).resolve()

        if not target_path.is_relative_to(self.root_path):
            raise PermissionError(
                f"Security Violation: Truy cập bị từ chối! Đường dẫn {filepath} nằm ngoài thư mục cho phép."
            )

        return target_path

    def connect(self):
        self._connected = True
        print(f"[MCPClient] Connected. Root path locked at: {self.root_path}")

    def disconnect(self):
        self._connected = False
        print("[MCPClient] Disconnected. Resources freed.")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def readFile(self, filepath: str) -> str:
        if not self._connected:
            raise RuntimeError("MCPClient chưa được kết nối. Vui lòng gọi connect() trước.")

        safe_path = self._validatePath(filepath)

        if not safe_path.exists() or not safe_path.is_file():
            raise FileNotFoundError(f"Không tìm thấy file hợp lệ tại: {safe_path}")

        try:
            with open(safe_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            raise IOError(f"Lỗi khi đọc file {safe_path}: {str(e)}")


if __name__ == "__main__":
    test_workspace = "./legacy_code_workspace"
    os.makedirs(test_workspace, exist_ok=True)

    valid_file = os.path.join(test_workspace, "main.py")
    with open(valid_file, "w") as f:
        f.write("print('Hello, legacy system!')")

    print("--- Test 1: Truy cập hợp lệ & Quản lý tài nguyên ---")
    with MCPClient(test_workspace) as client:
        content = client.readFile(valid_file)
        print(f"Nội dung file:\n{content}")

    print("\n--- Test 2: Tấn công Directory Traversal ---")
    try:
        with MCPClient(test_workspace) as client:
            malicious_path = os.path.join(test_workspace, "../mcp_client.py")
            client.readFile(malicious_path)
    except PermissionError as e:
        print(f"Thành công chặn đứng tấn công: {e}")