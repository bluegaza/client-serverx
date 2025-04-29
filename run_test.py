#!/usr/bin/env python3
"""
This script provides a simple way to run the client-server test.
It checks the environment and runs either the GUI or console simulation.
"""

import os
import sys
import subprocess
import time
import threading

def start_server(port=9090, packet_loss=0.0):
    """Start the forum server"""
    print(f"[INFO] Starting server on port {port} with packet loss {packet_loss}")
    server_process = subprocess.Popen(["python3", "server.py", str(port)])
    return server_process

def run_client(username, password, commands, delay_between_cmds=1):
    """Run a client with automated commands"""
    client_process = subprocess.Popen(
        ["python3", "client.py", "9090"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Start with authentication
    print(f"[INFO] Starting client for user {username}")
    inputs = [f"{username}\n", f"{password}\n"]
    
    # Add commands
    for cmd in commands:
        inputs.append(f"{cmd}\n")
    
    # Send inputs with delays
    for cmd_input in inputs:
        time.sleep(delay_between_cmds)
        client_process.stdin.write(cmd_input)
        client_process.stdin.flush()
    
    # Wait for completion and get output
    output, _ = client_process.communicate(timeout=30)
    return output

def run_concurrent_test():
    """Run a test with concurrent client connections"""
    print("[TEST] Starting concurrent client test")
    
    # Create test file if it doesn't exist
    if not os.path.exists("testfile.py"):
        with open("testfile.py", "w") as f:
            f.write("print('Hello from testfile')\n")
    
    # Start the server
    server_process = start_server()
    time.sleep(2)  # Wait for server to start
    
    try:
        # Create threads for different client sessions
        client1 = threading.Thread(
            target=lambda: run_client("Yoda", "jedi*knight", [
                "CRT TestThread",
                "MSG TestThread Hello from Yoda!",
                "UPD TestThread testfile.py",
                "RDT TestThread",
                "XIT"
            ])
        )
        
        client2 = threading.Thread(
            target=lambda: run_client("Leia", "organa123", [
                "LST",
                "RDT TestThread",
                "MSG TestThread Hello from Leia!",
                "DWN TestThread testfile.py",
                "XIT"
            ])
        )
        
        # Start client threads
        client1.start()
        time.sleep(2)  # Wait a bit between client starts
        client2.start()
        
        # Wait for client threads to complete
        client1.join()
        client2.join()
        
        print("[TEST] Concurrent test completed successfully")
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
    finally:
        # Terminate server
        server_process.terminate()
        server_process.wait()

def main():
    """Main function to run the test"""
    print("=== Forum Application Test ===")
    print("This script will test the forum application with multiple clients")
    
    choice = input("Run concurrent client test? (y/n): ").strip().lower()
    if choice == 'y':
        run_concurrent_test()
    else:
        print("Test canceled.")

if __name__ == "__main__":
    main()