import socket
import time
import sys

def unauthorized_access():
    print("Executing rogue processes...")
    
    # Attempt 1: Read sensitive host files
    try:
        with open('/etc/passwd', 'r') as f:
            print("CRITICAL SECURITY FAILURE: Read /etc/passwd")
    except Exception as e:
        print("Sandbox blocked host file access: " + str(e))

    # Attempt 2: Open an external network socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("8.8.8.8", 53))
        print("CRITICAL SECURITY FAILURE: Network outbound connection established")
    except Exception as e:
        print("Sandbox blocked network access: " + str(e))
        
    # Attempt 3: Memory exhaustion (OOM bomb)
    print("Starting memory allocation stress test. Awaiting timeout or OOM kill...")
    memory_hog = []
    while True:
        # Allocate ~10MB continuously
        memory_hog.append("x" * 10 * 1024 * 1024) 
        time.sleep(0.05)

if __name__ == "__main__":
    unauthorized_access()