import socket
import time
import sys
import os
import signal
import logging

SERVER_ADDRESS = '127.0.0.1'  # Change this to your server's IP address
SERVER_PORT = 12345  # Change this to your server's port
PID_FILE = "/tmp/daemon_client.pid" if not os.name == 'nt' else "daemon_client.pid"

# Set up logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename='./tmp/daemon_client.log', level=logging.DEBUG, format=LOG_FORMAT)

def send_request_to_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((SERVER_ADDRESS, SERVER_PORT))
            # Send a request to the server
            client_socket.sendall(b"Hello, server!")
            # Receive response from the serverlogger = logging.getLogger(__name__)
            response = client_socket.recv(1024)
            logging.info("Received from server: %s", response.decode("utf-8"))  # Specify encoding
    except Exception as e:
        logging.error("Error: %s", e)

def main():
    while True:
        send_request_to_server()
        time.sleep(5)  # Send request every 5 seconds

def start_daemon():
    if os.path.exists(PID_FILE):
        print("Daemon is already running.")
        sys.exit(1)

    if os.name == 'nt':
        main()
    else:
        from daemonize import Daemonize
        daemon = Daemonize(app="daemon_client", pid=PID_FILE, action=main)
        daemon.start()

def stop_daemon():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        os.remove(PID_FILE)
        logging.info("Daemon stopped.")
    else:
        logging.info("Daemon is not running.")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['start', 'stop']:
        print("Usage: python daemon_client.py [start|stop]")
        sys.exit(1)

    command = sys.argv[1]
    if command == 'start':
        start_daemon()
        logging.info("Daemon started.")
    elif command == 'stop':
        stop_daemon()
        logging.info("Daemon stopped.")
