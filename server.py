import socket
import threading

SERVER_ADDRESS = '127.0.0.1'
SERVER_PORT = 12345

def handle_client(client_socket):
    request = client_socket.recv(1024)
    print("Received request from client:", request.decode())

    # Check the request and send a response
    if request.strip() == b"Hello, server!":
        client_socket.sendall(b"Hello, client!")
    else:
        client_socket.sendall(b"Invalid request!")

    client_socket.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((SERVER_ADDRESS, SERVER_PORT))
        server_socket.listen(5)
        print("Server listening on", SERVER_ADDRESS, "port", SERVER_PORT)

        while True:
            client_socket, client_address = server_socket.accept()
            print("Accepted connection from", client_address)

            # Create a new thread to handle the client
            client_thread = threading.Thread(target=handle_client, args=(client_socket,))
            client_thread.start()

if __name__ == "__main__":
    start_server()
