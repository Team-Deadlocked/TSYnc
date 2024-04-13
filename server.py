import socket
import threading

SERVER_ADDRESS = '127.0.0.1'
SERVER_PORT = 12345

# Global variable to control the server loop
server_event = threading.Event()

def handle_client(client_socket):
    try:
        request = client_socket.recv(1024)
        print("Received request from client:", request.decode())

        # Check the request and send a response
        if request.strip() == b"Hello, server!":
            response = b"Hello, client!"
        else:
            response = b"Invalid request!"

        # Send the response back to the client
        client_socket.sendall(response)
    except Exception as e:
        print("Error handling client:", e)
    finally:
        client_socket.close()

def start_server():
    global server_event
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
        server_socket.listen(5)
        print("Server listening on", SERVER_ADDRESS, "port", SERVER_PORT)

        while not server_event.is_set():
            try:
                server_socket.settimeout(1)  # Timeout for non-blocking check
                client_socket, client_address = server_socket.accept()
                server_socket.settimeout(None)  # Reset timeout
                print("Accepted connection from", client_address)

                # Create a new thread to handle the client
                client_thread = threading.Thread(target=handle_client, args=(client_socket,))
                client_thread.start()
            except socket.timeout:
                # Check if the server event is set
                if server_event.is_set():
                    break  # Exit the loop if the server is stopping
            except Exception as e:
                print("Error accepting clients:", e)

def stop_server():
    global server_event
    print("Stopping server...")
    server_event.set()

def input_thread():
    input("Press Enter to stop the server...\n")
    stop_server()

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.start()

    input_thread = threading.Thread(target=input_thread)
    input_thread.start()

    # Wait for the server thread to finish
    server_thread.join()
