import os
from typing import List

def process_logs(file_paths: List[str]) -> List[str]:
    results: List[str] = []
    for path in file_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
            results.append(f"Processed file: {path} | Size: {len(data)} bytes")
        else:
            results.append(f"Error: {path} not found.")
    return results

def test_process_logs() -> None:
    # Simple inline test for the sandbox to execute
    test_file = "dummy_test.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("legacy system log entry")
    
    output = process_logs([test_file, "missing.txt"])
    
    assert len(output) == 2
    assert "Processed file" in output[0]
    assert "Error" in output[1]
    
    os.remove(test_file)
    print("Test passed.")

if __name__ == "__main__":
    test_process_logs()
