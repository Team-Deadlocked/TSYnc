import time
import multiprocessing
import threading
import sys

# Global variable to control the daemon process
daemon_running = False

# Define the function that will continuously check for events
def event_checker():
    while daemon_running:
        # Implement your event checking logic here
        print("Checking for events...")
        time.sleep(5)  # Sleep for 5 seconds between each check

# Define the function that will run the event checker in the background
def run_background():
    global daemon_running
    daemon_running = True
    event_process = multiprocessing.Process(target=event_checker)
    event_process.start()
    event_process.join()  # Wait for the process to finish (which it never will)
    daemon_running = False

# Main function to start or stop the background process
def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['start', 'stop']:
        print("Usage: python script.py [start|stop]")
        sys.exit(1)

    if sys.argv[1] == 'start':
        background_thread = threading.Thread(target=run_background)
        background_thread.daemon = True  # Daemonize the thread so it doesn't prevent program exit
        background_thread.start()
        print("Daemon started.")
    elif sys.argv[1] == 'stop':
        global daemon_running
        daemon_running = False
        print("Daemon stopped.")

if __name__ == "__main__":
    main()
