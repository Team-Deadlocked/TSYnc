import signal
import socket
import time
import sys
import os

# Check if the current platform is Windows
WINDOWS = os.name == 'nt'

SERVER_ADDRESS = '127.0.0.1'  # Change this to your server's IP address
SERVER_PORT = 12345  # Change this to your server's port
PID_FILE = "/tmp/daemon_client.pid" if not WINDOWS else "daemon_client.pid"

def send_request_to_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((SERVER_ADDRESS, SERVER_PORT))
            # Send a request to the server
            client_socket.sendall(b"Hello, server!")
            # Receive response from the server
            response = client_socket.recv(1024)
            print("Received from server:", response.decode())
    except Exception as e:
        print("Error:", e)

def main():
    while True:
        send_request_to_server()
        time.sleep(5)  # Send request every 5 seconds

def start_daemon():
    # On Windows, we can't daemonize, so just start the main function directly
    if WINDOWS:
        main()
    else:
        from daemonize import Daemonize
        daemon = Daemonize(app="daemon_client", pid=PID_FILE, action=main)
        daemon.start()

def stop_daemon():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        if WINDOWS:
            os.system(f"taskkill /F /PID {pid}")
        else:
            os.kill(pid, signal.SIGTERM)
        os.remove(PID_FILE)
        print("Daemon stopped.")
    else:
        print("Daemon is not running.")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['start', 'stop']:
        print("Usage: python daemon_client.py [start|stop]")
        sys.exit(1)

    command = sys.argv[1]
    if command == 'start':
        start_daemon()
        print("Daemon started.")
    elif command == 'stop':
        stop_daemon()
        print("Daemon stopped.")
