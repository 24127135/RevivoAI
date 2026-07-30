import os
import shutil
from mcp_client import MCPClient

def test_kan61_core_io():
    print("--- BẮT ĐẦU KIỂM THỬ KAN-61 (CORE I/O) ---")

    # 1. Thiết lập thư mục gốc (workspace) cho test
    test_root_path = "./temp_workspace"
    if not os.path.exists(test_root_path):
        os.makedirs(test_root_path)

    print(f"[*] Đã tạo thư mục gốc giả lập tại: {test_root_path}")

    try:
        # 2. Khởi tạo Client
        client = MCPClient(server_uri="http://localhost:8080", allowed_root_path=test_root_path)

        # 3. Test connect()
        print("\n[Test 1] Kết nối Client...")
        client.connect()

        # 4. Test writeFile()
        print("\n[Test 2] Ghi file...")
        file_path = "test_note.txt"
        content_to_write = "Đây là nội dung test cho RevivoAI."

        is_written = client.writeFile(file_path, content_to_write)
        assert is_written == True, "Lỗi: writeFile trả về False"
        print("  -> OK: writeFile hoạt động thành công.")

        # Thử ghi vào một thư mục con chưa tồn tại (để test os.makedirs)
        client.writeFile("logs/execution_log.json", '{"status": "success"}')
        print("  -> OK: writeFile (tạo thư mục con tự động) hoạt động thành công.")

        # 5. Test readFile()
        print("\n[Test 3] Đọc file...")
        read_content = client.readFile(file_path)
        assert read_content == content_to_write, "Lỗi: Nội dung đọc ra không khớp với nội dung đã ghi!"
        print("  -> OK: readFile đọc nội dung chính xác.")

        # 6. Test listDirectory()
        print("\n[Test 4] Duyệt thư mục...")
        # Duyệt thư mục gốc (truyền vào thư mục hiện tại "." hoặc "")
        dir_items = client.listDirectory("")
        print(f"  -> Nội dung tìm thấy: {dir_items}")
        assert "test_note.txt" in dir_items, "Lỗi: Thiếu test_note.txt trong danh sách"
        assert "logs" in dir_items, "Lỗi: Thiếu thư mục 'logs' trong danh sách"
        print("  -> OK: listDirectory lấy đúng danh sách file/folder.")

        # 7. Test disconnect()
        print("\n[Test 5] Ngắt kết nối...")
        client.disconnect()

        print("\n--- ✅ TẤT CẢ TEST KAN-61 ĐỀU PASS! ---")

    except Exception as e:
        print(f"\n❌ TEST THẤT BẠI VỚI LỖI: {e}")

    finally:
        # 8. Clean up - Dọn dẹp thư mục test
        print("\n[*] Đang dọn dẹp workspace ảo...")
        if os.path.exists(test_root_path):
            shutil.rmtree(test_root_path)
            print("  -> Đã xóa thư mục test.")


if __name__ == "__main__":
    test_kan61_core_io()