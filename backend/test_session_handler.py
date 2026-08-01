import os
import sys
import uuid
import asyncio
import logging

# Tự động trỏ import path về thư mục backend/ (project root của Python)
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Import chính xác vì session_handler.py nằm ở backend/
from session_handler import SessionHandler
from core.database import supabase_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_integration_tests():
    logger.info("Starting SessionHandler integration tests...")

    handler = SessionHandler()
    test_user_id = str(uuid.uuid4())
    session_id = None

    try:
        # 1. SETUP: Tạo User giả để thỏa mãn khóa ngoại (Foreign Key)
        logger.info("--- Setup: Creating Dummy User ---")
        user_payload = {
            "user_id": test_user_id,
            "email": f"test_{uuid.uuid4().hex[:8]}@revivoai.local",
            "username": f"testuser_{uuid.uuid4().hex[:6]}",
        }
        supabase_db.table("User").insert(user_payload).execute()

        # 2. TEST: Khởi tạo Session và Workspace vật lý
        logger.info("--- Test 1: Initialize Session ---")
        session_id = await handler.initialize_session(test_user_id)
        assert session_id is not None, "Failed to initialize session"
        logger.info(f"Initialized Session ID: {session_id}")

        # 3. TEST: Kiểm tra Workspace Directory có tồn tại không
        logger.info("--- Test 2: Verify Workspace Exists ---")
        session_data = await handler.get_session(session_id)
        assert session_data is not None, "Could not fetch session from DB"

        workspace_path = session_data.get("workspace_path")
        assert os.path.exists(workspace_path), f"Workspace path does not exist: {workspace_path}"
        logger.info(f"Verified workspace directory created at: {workspace_path}")

        # 4. TEST: Cập nhật trạng thái Session
        logger.info("--- Test 3: Update Session Status ---")
        updated = await handler.update_session_status(session_id, "deactivated")
        # Đã đổi thành assert is_active is False
        assert updated["is_active"] is False, "Status was not updated correctly"
        logger.info(f"Session status updated. is_active: {updated['is_active']}")

        # 5. TEST: Hủy Session (Xóa thư mục và đổi is_active thành False)
        logger.info("--- Test 4: Destroy Session ---")
        destroyed = await handler.destroy_session(session_id)
        assert destroyed is True, "Failed to destroy session"
        assert not os.path.exists(workspace_path), "Workspace directory was NOT deleted!"

        final_session = await handler.get_session(session_id)
        assert final_session["is_active"] is False, "Session DB is_active is not False"
        logger.info("Session destroyed, DB marked inactive, and workspace cleaned up.")

        logger.info("✅ All SessionHandler tests passed successfully!")

    except AssertionError as e:
        logger.error(f"❌ Test Assertion Failed: {e}")
    except Exception as e:
        logger.error(f"❌ Test Execution Failed: {e}")

    finally:
        # 6. CLEANUP: Dọn dẹp dữ liệu rác trong Supabase
        logger.info("--- Cleanup: Removing test data from Database ---")
        if session_id:
            # Đã sửa thành cột "session_id"
            supabase_db.table("Session").delete().eq("session_id", session_id).execute()
        supabase_db.table("User").delete().eq("user_id", test_user_id).execute()
        logger.info("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(run_integration_tests())