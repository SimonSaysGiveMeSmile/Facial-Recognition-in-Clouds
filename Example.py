import socket

HOST, PORT = '', 8000
# Create an socket object
with socket.socket() as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"Server is listening on {HOST}:{PORT}")
    
    # Wait for connections and handle arrivals
    while True:
        conn, addr = server_socket.accept()
        print(f"Client connected from {addr}")
        data = conn.recv(1024)
        print(f"Received data: {data.decode()}")
        conn.sendall(b"Hello from the server!")
        
        