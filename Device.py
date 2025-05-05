import datetime
import hashlib
import os
import socket
import threading
import time

print_lock = threading.Lock()

devices = []
buffer = {}

PORT = 5007
INTERVAL = 5
BROADCAST_IP = '255.255.255.255'

NODE_NAME = os.getenv("NODE_NAME", socket.gethostname())


def get_own_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def send_heartbeat():
    my_ip = get_own_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        message = f"[HEARTBEAT] {NODE_NAME} {my_ip}"
        sock.sendto(message.encode(), (BROADCAST_IP, PORT))
        with print_lock:
            print(f"[{NODE_NAME}] Enviado: {message}")
        time.sleep(INTERVAL)


def server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', PORT))

    while True:
        data, addr = sock.recvfrom(1024)

        # descarta as mensagens enviadas por si mesmo via broadcast
        if not addr[0] == get_own_ip():
            message = data.decode().strip()
            protocol = message.split(' ')[0]

            if protocol == "[HEARTBEAT]":
                heartbeat(addr, data)
            elif protocol == "[TALK]":
                talk(addr, message)
            elif protocol == "[FILE]":
                receive_file_ack(addr, message)
            elif protocol == "[CHUNK]":
                receive_file_chunk(message)
            elif protocol == "[END]":
                receive_end_of_file(addr, message)
            elif protocol == "[AKC]":
                continue
            elif protocol == "[NACK]":
                continue


def talk(addr, message):
    sender_ip = addr[0]

    tokens = message.split(' ')
    message_id = tokens[1]

    ack_message = f"[ACK] {message_id}"
    send_message(sender_ip, ack_message, PORT)


def heartbeat(addr, data):
    sender_ip = addr[0]
    message = data.decode().strip()
    node_name = message.split(' ')[1]

    with print_lock:
        print(f"[{NODE_NAME}] Recebido de {sender_ip}: {data.decode().strip()}")

    does_exist = False
    for device in devices:
        if device["ip"] == sender_ip:
            device["time"] = datetime.datetime.now()
            does_exist = True

    if not does_exist:
        devices.append({
            "ip": sender_ip,
            "name": node_name,
            "time": datetime.datetime.now()
        })


def receive_file_ack(addr, message):
    sender_ip = addr[0]
    tokens = message.split(' ')
    message_id = tokens[1]
    filepath = tokens[2]

    ack_message = f"[ACK] {message_id} {filepath}"
    send_message(sender_ip, ack_message, PORT)


def receive_file_chunk(message):
    chunk = message.removeprefix(b"[CHUNK] ")

    try:
        seq_str, chunk = chunk.split(b"|", 1)
        seq = int(seq_str)
        buffer[seq] = chunk
    except Exception as e:
        print("Erro ao processar pacote:", e)


def receive_end_of_file(addr, message):
    sender_ip = addr[0]
    tokens = message.split(' ')
    message_id = tokens[1]
    received_hash = tokens[2]
    filepath = tokens[3]

    print("Antes de escrever arquivo")
    with open(filepath, "wb") as f:
        for seq in sorted(buffer):
            f.write(buffer[seq])

    print("Depois de escrever arquivo")

    test_hash = sha256_of_file(filepath)

    new_message = get_message(message_id, received_hash, test_hash)

    send_message(sender_ip, new_message, PORT)


def get_message(message_id, received_hash, test_hash):
    if received_hash == test_hash:
        print("Hash matched")
        return f"[ACK] {message_id}"
    else:
        print("Hash mismatched")
        return f"[NACK] {message_id} Hash Mismatch"


def send_message(ip, message, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        while True:
            sock.sendto(message.encode(), (ip, port))
            with print_lock:
                print(f"[{NODE_NAME}] Enviado para {ip}:{PORT}: {message}")
    finally:
        sock.close()


def sha256_of_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


if __name__ == "__main__":
    threading.Thread(target=server, daemon=True).start()
    send_heartbeat()
