import os
import uuid
from enum import Enum
from typing import List, Optional

class ConnectionStatus(Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


class MCPClient:
    def __init__(self, server_uri: str, allowed_root_path: str, session_id: Optional[str] = None,
                 timeout_ms: int = 5000):
        self.__server_uri: str = server_uri
        self.__allowed_root_path: str = allowed_root_path
        self.__session_id: str = session_id if session_id else str(uuid.uuid4())
        self.__connection_status: ConnectionStatus = ConnectionStatus.DISCONNECTED
        self._timeout_ms: int = timeout_ms

    def connect(self) -> bool:
        self.__connection_status = ConnectionStatus.CONNECTED
        print(f"[MCPClient] Connected. Session ID: {self.__session_id}")
        return True

    def disconnect(self) -> None:
        self.__connection_status = ConnectionStatus.DISCONNECTED
        print("[MCPClient] Disconnected.")

    def readFile(self, path: str) -> str:
        if not self.__validatePath(path):
            raise PermissionError(f"Security Violation: Truy cập bị từ chối!")

        full_path = os.path.join(self.__allowed_root_path, path)
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()

    def writeFile(self, path: str, content: str) -> bool:
        if not self.__validatePath(path):
            raise PermissionError(f"Security Violation: Truy cập bị từ chối!")

        full_path = os.path.join(self.__allowed_root_path, path)
        try:
            # Tạo thư mục cha nếu chưa tồn tại
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"[MCPClient] writeFile Error: {e}")
            return False

    def listDirectory(self, path: str) -> List[str]:
        if not self.__validatePath(path):
            raise PermissionError(f"Security Violation: Truy cập bị từ chối!")
        full_path = os.path.join(self.__allowed_root_path, path)
        if not os.path.isdir(full_path):
            raise NotADirectoryError(f"Đường dẫn không phải là thư mục: {path}")
        return os.listdir(full_path)