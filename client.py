import socket
import os
import json
from utils import calculate_hash, get_all_files

#change if needed
SERVER_IP = '127.0.0.1'  
PORT = 9001
BUFFER_SIZE = 4096

def send_file(sock, file_path, relative_path):
    file_size = os.path.getsize(file_path)
    print(f"[INFO] Sending file: {relative_path} ({file_size} bytes)")


    file_name_bytes = relative_path.encode()
    sock.sendall(len(file_name_bytes).to_bytes(4, 'big'))
    sock.sendall(file_name_bytes)

    sock.sendall(file_size.to_bytes(8, 'big'))

    with open(file_path, 'rb') as f:
        while chunk := f.read(BUFFER_SIZE):
            sock.sendall(chunk)

    print(f"[DONE] File sent: {relative_path}")

def send_metadata(sock, relative_path, file_hash, file_size):
    metadata = {
        'type': 'metadata',
        'filename': relative_path,
        'hash': file_hash,
        'size': file_size
    }
    msg = json.dumps(metadata).encode()
    sock.sendall(len(msg).to_bytes(4, 'big'))  
    sock.sendall(msg)


    resp_len = int.from_bytes(sock.recv(4), 'big')
    resp_json = sock.recv(resp_len).decode()
    response = json.loads(resp_json)
    return response.get("status", "send") 

def sync_directory(base_dir):
    all_files = get_all_files(base_dir)
    print(f"[INFO] Found {len(all_files)} files to check")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_IP, PORT))
        print(f"[CONNECTED] Server: {SERVER_IP}:{PORT}")

        for full_path, rel_path in all_files:
            file_size = os.path.getsize(full_path)
            file_hash = calculate_hash(full_path)

            status = send_metadata(sock, rel_path, file_hash, file_size)
            if status == "send":
                send_file(sock, full_path, rel_path)
            else:
                print(f"[SKIPPED] {rel_path} already exists on server")

if __name__ == "__main__":
    folder_path = input("Enter path of directory to sync: ").strip()

    if not os.path.isdir(folder_path):
        print("[ERROR] Invalid directory path.")
    else:
        sync_directory(folder_path)
