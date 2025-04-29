import socket
import random
import sys
import os
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ForumClient")

# Constants
BUFFER_SIZE = 1024
ACK_TIMEOUT = 2
MAX_RETRIES = 3
SERVER_IP = "127.0.0.1"  # localhost

class ForumClient:
    def __init__(self, server_port):
        """Initialize the client"""
        self.server_addr = (SERVER_IP, server_port)
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_sock.settimeout(ACK_TIMEOUT)
        self.username = None
        self.is_authenticated = False
        
    def simulate_packet_loss(self, packet_loss_rate=0.0):
        """Simulate packet loss for testing reliability"""
        return random.random() < packet_loss_rate
        
    def reliable_send(self, data, packet_loss_rate=0.0):
        """Send data reliably using a simple ARQ protocol"""
        seq_num = random.randint(0, 10000)
        packet = f"{seq_num}|{data}".encode()
        
        attempts = 0
        while attempts < MAX_RETRIES:
            if not self.simulate_packet_loss(packet_loss_rate):
                self.udp_sock.sendto(packet, self.server_addr)
            
            try:
                ack_data, _ = self.udp_sock.recvfrom(BUFFER_SIZE)
                ack_seq = int(ack_data.decode())
                if ack_seq == seq_num:
                    return True
            except socket.timeout:
                logger.debug(f"Timeout waiting for ACK {seq_num}, retrying...")
                attempts += 1
            except ValueError:
                continue
                
        logger.error("Failed to send data after multiple attempts")
        return False
        
    def reliable_recv(self, packet_loss_rate=0.0):
        """Receive data reliably using a simple ARQ protocol"""
        while True:
            try:
                data, addr = self.udp_sock.recvfrom(BUFFER_SIZE)
                if self.simulate_packet_loss(packet_loss_rate):
                    logger.debug("Simulated packet loss")
                    continue
                    
                try:
                    decoded = data.decode()
                    if '|' in decoded:
                        seq_num, payload = decoded.split('|', 1)
                        self.udp_sock.sendto(seq_num.encode(), addr)
                        return payload
                    else:
                        return decoded
                except UnicodeDecodeError:
                    # Binary data
                    parts = data.split(b'|', 2)
                    if len(parts) >= 3:
                        seq_num = parts[0].decode()
                        self.udp_sock.sendto(seq_num.encode(), addr)
                        return parts[2]
            except socket.timeout:
                return None
            except Exception as e:
                logger.error(f"Error in reliable_recv: {e}")
                continue
                
    def authenticate(self):
        """Authenticate user with the server"""
        while True:
            username = input("Enter username: ").strip()
            
            if not username:
                print("Username cannot be empty.")
                continue
                
            self.reliable_send(username)
            response = self.reliable_recv()
            
            if response == "Username in use":
                print("This username is currently in use. Please choose another.")
                continue
            elif response == "Invalid username":
                print("Invalid username. Please try again.")
                continue
            elif response == "Username OK":
                # Existing user, enter password
                password = input("Enter password: ").strip()
                self.reliable_send(password)
                login_response = self.reliable_recv()
                
                if login_response == "Welcome":
                    self.username = username
                    self.is_authenticated = True
                    print(f"Welcome back, {username}!")
                    break
                else:
                    print("Invalid password. Please try again.")
            elif response == "New User":
                # New user, create account
                password = input("Create a password: ").strip()
                self.reliable_send(password)
                create_response = self.reliable_recv()
                
                if create_response and "Account Created" in str(create_response):
                    self.username = username
                    self.is_authenticated = True
                    print(f"Account created successfully. Welcome, {username}!")
                    break
                else:
                    print("Failed to create account. Please try again.")
            else:
                print(f"Unexpected response from server: {response}")
                
    def display_commands(self):
        """Display available commands"""
        print("\nAvailable commands:")
        print("CRT: Create Thread (Usage: CRT threadtitle)")
        print("LST: List Threads")
        print("MSG: Post Message (Usage: MSG threadtitle message)")
        print("DLT: Delete Message (Usage: DLT threadtitle messagenumber)")
        print("RDT: Read Thread (Usage: RDT threadtitle)")
        print("EDT: Edit Message (Usage: EDT threadtitle messagenumber message)")
        print("UPD: Upload File (Usage: UPD threadtitle filename)")
        print("DWN: Download File (Usage: DWN threadtitle filename)")
        print("RMV: Remove Thread (Usage: RMV threadtitle)")
        print("XIT: Exit")
        
    def upload_file(self, thread_title, filename):
        """Upload a file to the server using TCP"""
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found")
            return
            # Send upload request via UDP
        self.reliable_send(f"UPD {thread_title} {filename}")
        response = self.reliable_recv()
        
        if not response or "Ready for TCP transfer" not in str(response):
            print(f"Error: {response}")
            return
            
        try:
            # Create TCP socket for file transfer
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((SERVER_IP, self.server_addr[1]))
            
            # Read and send file
            with open(filename, 'rb') as f:
                data = f.read(BUFFER_SIZE)
                while data:
                    tcp_sock.sendall(data)
                    data = f.read(BUFFER_SIZE)
                    
            # Close the TCP connection
            time.sleep(0.1)  # Small delay to ensure all data is sent
            tcp_sock.close()
            
            # Wait for UDP confirmation
            upload_result = self.reliable_recv()
            print(upload_result)
            
        except Exception as e:
            print(f"Upload error: {e}")
            
    def download_file(self, thread_title, filename):
        """Download a file from the server using TCP"""
        # Send download request via UDP
        self.reliable_send(f"DWN {thread_title} {filename}")
        response = self.reliable_recv()
        
        if not response or "Ready for TCP transfer" not in str(response):
            print(f"Error: {response}")
            return
            
        try:
            # Extract file size if provided
            file_size = None
            if response and isinstance(response, str) and "|" in response:
                parts = response.split("|")
                if len(parts) > 1:
                    try:
                        file_size = int(parts[1])
                    except ValueError:
                        pass
            
            # Create TCP socket for file transfer
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.connect((SERVER_IP, self.server_addr[1]))
            
            # Receive and save file
            received = 0
            with open(filename, 'wb') as f:
                while True:
                    data = tcp_sock.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
                    
                    # Print progress if file size is known
                    if file_size:
                        progress = int((received / file_size) * 100)
                        print(f"\rDownloading: {progress}%", end="")

            print()  # New line after progress
            
            # Close the TCP connection
            tcp_sock.close()
            
            # Wait for UDP confirmation
            download_result = self.reliable_recv()
            print(download_result)
            
        except Exception as e:
            print(f"Download error: {e}")
            
    def run(self):
        """Main client loop"""
        print("=== Welcome to the Forum Application ===")
        
        # Authenticate with the server
        self.authenticate()
        
        if not self.is_authenticated:
            print("Authentication failed. Exiting.")
            return
            
        # Display available commands
        self.display_commands()
        
        # Main command loop
        while True:
            try:
                command = input("\nEnter command: ").strip()
                
                if not command:
                    continue
                    
                # Handle file upload/download separately
                if command.upper().startswith("UPD "):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print("Invalid command format. Use: UPD threadtitle filename")
                        continue
                    self.upload_file(parts[1], parts[2])
                    continue
                    
                if command.upper().startswith("DWN "):
                    parts = command.split(" ", 2)
                    if len(parts) < 3:
                        print("Invalid command format. Use: DWN threadtitle filename")
                        continue
                    self.download_file(parts[1], parts[2])
                    continue
                    
                # Send command to server
                self.reliable_send(command)
                response = self.reliable_recv()
                
                if response:
                    print(response)
                    
                # Exit if the command was XIT
                if command.upper() == "XIT":
                    break
                    
            except KeyboardInterrupt:
                print("\nInterrupted by user. Exiting...")
                # Try to gracefully exit
                try:
                    self.reliable_send("XIT")
                    self.reliable_recv()  # Receive goodbye message
                except:
                    pass
                break
                
            except Exception as e:
                print(f"Error: {e}")
                
        print("Goodbye!")
        self.udp_sock.close()

def main():
    """Main entry point for the client application"""
    if len(sys.argv) != 2:
        print("Usage: python client.py <server_port>")
        sys.exit(1)
        
    try:
        server_port = int(sys.argv[1])
        client = ForumClient(server_port)
        client.run()
    except ValueError:
        print("Error: Port must be a number")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
