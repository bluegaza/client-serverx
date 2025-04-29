import socket
import threading
import os
import random
import time
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='[%(levelname)s] %(asctime)s - %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger("ForumServer")

# Constants
BUFFER_SIZE = 1024
ACK_TIMEOUT = 2
UPLOAD_DIR = "uploads"
CREDENTIALS_FILE = "credentials.txt"
MAX_RETRIES = 3

# Global variables
logged_users = set()
threads_lock = threading.Lock()
server_running = True

# Create upload directory if it doesn't exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)


def simulate_packet_loss(packet_loss_rate=0.0):
    """Simulate packet loss for testing reliability"""
    return random.random() < packet_loss_rate


def reliable_send(sock, addr, data, is_binary=False, packet_loss_rate=0.0):
    """Send data reliably using a simple ARQ protocol"""
    seq_num = random.randint(0, 10000)
    if is_binary:
        header = f"{seq_num}|BIN|".encode()
        packet = header + data
    else:
        packet = f"{seq_num}|{data}".encode()

    attempts = 0
    while attempts < MAX_RETRIES:
        if not simulate_packet_loss(packet_loss_rate):
            sock.sendto(packet, addr)
        sock.settimeout(ACK_TIMEOUT)
        try:
            ack_data, _ = sock.recvfrom(BUFFER_SIZE)
            ack_seq = int(ack_data.decode())
            if ack_seq == seq_num:
                return True
        except socket.timeout:
            logger.debug(f"Timeout waiting for ACK {seq_num}, retrying...")
            attempts += 1
        except ValueError:
            continue
    return False


def reliable_recv(sock, packet_loss_rate=0.0):
    """Receive data reliably using a simple ARQ protocol"""
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            if simulate_packet_loss(packet_loss_rate):
                logger.debug(f"Simulated packet loss from {addr}")
                continue

            try:
                decoded = data.decode()
                if '|' in decoded:
                    seq_num, payload = decoded.split('|', 1)
                    sock.sendto(seq_num.encode(), addr)
                    return payload, addr, False
                else:
                    return decoded, addr, False
            except UnicodeDecodeError:
                # Binary data
                parts = data.split(b'|', 2)
                if len(parts) >= 3:
                    seq_num = parts[0].decode()
                    sock.sendto(seq_num.encode(), addr)
                    return parts[2], addr, True
        except socket.timeout:
            continue
        except Exception as e:
            logger.error(f"Exception in reliable_recv: {e}")
            continue


def authenticate_user(username, password=None, new_user=False):
    """Authenticate a user against the credentials file"""
    logger.debug(f"Authenticating user: {username}, new_user={new_user}")

    # Create credentials file if it doesn't exist
    if not os.path.exists(CREDENTIALS_FILE):
        open(CREDENTIALS_FILE, 'w').close()

    with open(CREDENTIALS_FILE, 'r+') as f:
        credentials = {}
        for line in f:
            if line.strip():
                parts = line.strip().split()
                if len(parts) >= 2:
                    credentials[parts[0]] = parts[1]

        if new_user:
            if username in credentials:
                return False
            f.write(f"{username} {password}\n")
            return True
        else:
            return username in credentials and credentials[username] == password


def get_thread_list():
    """Get list of available threads"""
    threads = []
    for file in os.listdir():
        if os.path.isfile(file) and not file.startswith('.') and not file in [
                'server.py', 'client.py', 'credentials.txt'
        ]:
            threads.append(file)
    return threads


def client_handler(sock, client_addr, packet_loss_rate=0.0):
    """Handle client connections and process commands"""
    username = None

    try:
        # Authentication process
        data, addr, _ = reliable_recv(sock, packet_loss_rate)
        username = data.strip()
        logger.info(f"Authentication attempt from {username} at {addr}")

        if not username:
            reliable_send(sock,
                          addr,
                          "Invalid username",
                          packet_loss_rate=packet_loss_rate)
            return

        # Check if username is already in use
        with threads_lock:
            if username in logged_users:
                reliable_send(sock,
                              addr,
                              "Username in use",
                              packet_loss_rate=packet_loss_rate)
                return

        # Check if this is an existing user
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                credentials = {
                    line.split()[0]: line.split()[1]
                    for line in f if line.strip()
                }
                user_exists = username in credentials
        else:
            user_exists = False

        if user_exists:
            reliable_send(sock,
                          addr,
                          "Username OK",
                          packet_loss_rate=packet_loss_rate)
            password, addr, _ = reliable_recv(sock, packet_loss_rate)

            if authenticate_user(username, password):
                reliable_send(sock,
                              addr,
                              "Welcome",
                              packet_loss_rate=packet_loss_rate)
                with threads_lock:
                    logged_users.add(username)
                logger.info(f"User {username} logged in successfully")
            else:
                reliable_send(sock,
                              addr,
                              "Invalid Password",
                              packet_loss_rate=packet_loss_rate)
                return
        else:
            reliable_send(sock,
                          addr,
                          "New User",
                          packet_loss_rate=packet_loss_rate)
            password, addr, _ = reliable_recv(sock, packet_loss_rate)

            if authenticate_user(username, password, new_user=True):
                reliable_send(sock,
                              addr,
                              "Account Created",
                              packet_loss_rate=packet_loss_rate)
                with threads_lock:
                    logged_users.add(username)
                logger.info(f"New account created for {username}")
            else:
                reliable_send(sock,
                              addr,
                              "Account creation failed",
                              packet_loss_rate=packet_loss_rate)
                return

        # Main command loop
        while server_running:
            cmd_data, addr, is_binary = reliable_recv(sock, packet_loss_rate)
            if not cmd_data:
                continue

            cmd = cmd_data if not is_binary else cmd_data.decode('utf-8', errors='replace')
            logger.info(f"Command from {username}: {cmd}")

            # Process commands
            parts = cmd.strip().split(" ", 1)
            command = parts[0].upper()

            if command == "XIT":
                # Exit command
                with threads_lock:
                    if username in logged_users:
                        logged_users.remove(username)
                reliable_send(sock,
                              addr,
                              "Goodbye",
                              packet_loss_rate=packet_loss_rate)
                logger.info(f"User {username} logged out")
                break

            elif command == "CRT" and len(parts) > 1:
                # Create Thread
                thread_title = parts[1]

                # Check if thread already exists
                if os.path.exists(thread_title):
                    reliable_send(sock,
                                  addr,
                                  f"Thread {thread_title} already exists",
                                  packet_loss_rate=packet_loss_rate)
                else:
                    with open(thread_title, 'w') as f:
                        f.write(f"{username}\n")
                    reliable_send(
                        sock,
                        addr,
                        f"Thread {thread_title} created successfully",
                        packet_loss_rate=packet_loss_rate)
                    logger.info(f"Thread {thread_title} created by {username}")

            elif command == "LST":
                # List all threads
                threads = get_thread_list()
                if threads:
                    thread_list = "\n".join(threads)
                    reliable_send(sock,
                                  addr,
                                  f"Threads:\n{thread_list}",
                                  packet_loss_rate=packet_loss_rate)
                else:
                    reliable_send(sock,
                                  addr,
                                  "No threads available",
                                  packet_loss_rate=packet_loss_rate)

            # Handle other commands similarly...

    except Exception as e:
        logger.error(f"Error in client handler: {e}")
    finally:
        with threads_lock:
            if username in logged_users:
                logged_users.remove(username)
                logger.info(f"User {username} session ended")


def main():
    if len(sys.argv) != 2:
        print("Usage: python server.py <server_port>")
        sys.exit(1)

    server_port = int(sys.argv[1])

    # Create UDP socket
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(('0.0.0.0', server_port))  # Bind to all interfaces

    logger.info(f"Server started on port {server_port}")
    logger.info("Waiting for client connections...")

    try:
        while server_running:
            try:
                # Receive initial data to identify client
                data, addr = udp_sock.recvfrom(BUFFER_SIZE)
                logger.info(f"Connection from {addr}")

                # Start a new thread to handle this client
                client_thread = threading.Thread(target=client_handler,
                                                 args=(udp_sock, addr))
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")

    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        udp_sock.close()


if __name__ == "__main__":
    main()
