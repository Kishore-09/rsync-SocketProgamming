import socket
import os
import json
import hashlib


HOST = '0.0.0.0'
PORT = 9001
BUFFER_SIZE = 4096
DEST_DIR = 'received_files'

os.makedirs(DEST_DIR, exist_ok=True)

def calculate_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()

def should_receive_file(file_path, client_hash):
    if not os.path.exists(file_path):
        return True
    local_hash = calculate_hash(file_path)
    return local_hash != client_hash

def receive_metadata(conn):
    try:
        raw = conn.recv(4)
        if not raw:
            return None
        msg_len = int.from_bytes(raw, 'big')
        metadata_json = conn.recv(msg_len).decode()
        metadata = json.loads(metadata_json)
        return metadata
    except Exception as e:
        print(f"[WARN] Could not receive metadata: {e}")
        return None


def send_json(conn, data):
    encoded = json.dumps(data).encode()
    conn.sendall(len(encoded).to_bytes(4, 'big'))
    conn.sendall(encoded)

def receive_file(conn, rel_path, file_size):
    file_path = os.path.join(DEST_DIR, rel_path)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    print(f"[INFO] Receiving file: {rel_path} ({file_size} bytes)")
    with open(file_path, 'wb') as f:
        received = 0
        while received < file_size:
            data = conn.recv(min(BUFFER_SIZE, file_size - received))
            if not data:
                break
            f.write(data)
            received += len(data)
            print(f"[INFO] Received {received}/{file_size} bytes", end='\r')
    print(f"\n[SAVED] File written to: {file_path}")

def handle_client(conn):
    while True:
        metadata = receive_metadata(conn)
        if metadata is None:
            break  

        if metadata.get("type") != "metadata":
            print("[WARN] Unknown message type, skipping")
            continue

        rel_path = metadata["filename"]
        client_hash = metadata["hash"]
        file_size = metadata["size"]

        dest_path = os.path.join(DEST_DIR, rel_path)
        decision = "send" if should_receive_file(dest_path, client_hash) else "skip"

        send_json(conn, {"status": decision})

        if decision == "send":
            name_len = int.from_bytes(conn.recv(4), 'big')
            conn.recv(name_len)  
            conn.recv(8)         
            receive_file(conn, rel_path, file_size)
        else:
            print(f"[SKIP] File already up-to-date: {rel_path}")


def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.bind((HOST, PORT))
        server_sock.listen(1)
        print(f"[READY] Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()
            print(f"[CONNECTED] Client: {addr}")
            with conn:
                handle_client(conn)
                print(f"[DISCONNECTED] Client: {addr}")

if __name__ == "__main__":
    start_server()

