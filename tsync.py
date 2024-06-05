import subprocess
import argparse
import os
import signal
import socket

# Define paths for the PID files
SERVER_PID_FILE = 'server.pid'
CLIENT_PID_FILE = 'client.pid'


def get_internal_ip():
    """Get the internal IP address of the current machine."""
    try:
        # Create a temporary socket to connect to a remote host (Google's DNS server)
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp_socket.connect(("8.8.8.8", 80))
        internal_ip = temp_socket.getsockname()[0]
        temp_socket.close()
        return internal_ip
    except socket.error as e:
        print(f"Failed to retrieve internal IP: {e}")
        return '127.0.0.1'  # Default to loopback address if failed


def get_username():
    """Get the username of the current user."""
    return os.getlogin()  # Get the current username


def start_processes(username, ip_address):
    """Start the server and client processes."""
    server_process = subprocess.Popen(
        ['python3', 'monitor.py', '-ip', ip_address, '-port', '8082', '-uname', username, '-role', 'client'])
    client_process = subprocess.Popen(
        ['python3', 'monitor.py', '-ip', ip_address, '-port', '8081', '-uname', username, '-role', 'server'])

    # Write the PIDs to files
    with open(SERVER_PID_FILE, 'w') as f:
        f.write(str(server_process.pid))
    with open(CLIENT_PID_FILE, 'w') as f:
        f.write(str(client_process.pid))

    print(f"Started server (PID {server_process.pid}) and client (PID {client_process.pid})")


def stop_process(pid_file):
    """Stop a process given its PID file."""
    if os.path.exists(pid_file):
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Stopped process with PID {pid}")
        except ProcessLookupError:
            print(f"No process with PID {pid} found")
        os.remove(pid_file)
    else:
        print(f"No PID file {pid_file} found")


def stop_processes():
    """Stop the server and client processes."""
    stop_process(SERVER_PID_FILE)
    stop_process(CLIENT_PID_FILE)


parser = argparse.ArgumentParser()
parser.add_argument('--command', choices=['start', 'stop'], required=True,
                    help='Command to start or stop the processes')

args = parser.parse_args()

username = get_username()
ip_address = get_internal_ip()

if args.command == 'start':
    start_processes(username, ip_address)
elif args.command == 'stop':
    stop_processes()
