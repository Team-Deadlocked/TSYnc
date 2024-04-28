import socket


HEADER = 64
PORT = 50532
FORMAT = 'utf-8'
DISCONNECT_MESSAGE= "!DISCONNECT"
#SERVER = socket.gethostbyname(socket.gethostname())
SERVER = "192.168.0.104"
#SERVER = "192.168.0.180"
ADDR = (SERVER,PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

def send(msg):
    message=msg.encode(FORMAT)
    msg_len = len(message)
    send_len = str(msg_len).encode(FORMAT)
    send_len += b' ' * (HEADER-len(send_len))
    client.send(send_len)
    client.send(message)



send("Hello from laptop!")
# inp=input()
# send(inp)
send(DISCONNECT_MESSAGE)