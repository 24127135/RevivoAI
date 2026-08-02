import os
from optparse import OptionParser

def process_logs(file_paths):
    results = []
    for i in range(len(file_paths)):
        path = file_paths[i]
        if os.path.exists(path):
            f = open(path, 'r')
            data = f.read()
            f.close()
            # Legacy string concatenation and manual formatting
            results.append("Processed file: " + str(path) + " | Size: " + str(len(data)) + " bytes")
        else:
            results.append("Error: " + str(path) + " not found.")
    return results

def test_process_logs():
    # Simple inline test for the sandbox to execute
    test_file = "dummy_test.txt"
    f = open(test_file, 'w')
    f.write("legacy system log entry")
    f.close()
    
    output = process_logs([test_file, "missing.txt"])
    
    assert len(output) == 2
    assert "Processed file" in output[0]
    assert "Error" in output[1]
    
    os.remove(test_file)
    print("Test passed.")

if __name__ == "__main__":
    test_process_logs()