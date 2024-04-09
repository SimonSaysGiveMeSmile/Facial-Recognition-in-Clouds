import socket

HOST, PORT = 'localhost', 8000
# Create a socket object using the default settings
with socket.socket() as client_socket:
    client_socket.connect((HOST, PORT))
    print(f"Connected to server at {HOST}:{PORT}")
    client_socket.sendall(b"Hello from the client!")
    data = client_socket.recv(1024)
    print(f"Received data: {data.decode()}")
    
    