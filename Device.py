import socket
import threading
import time

conexoes = []  # Lista global para armazenar conexões ativas

# Função para lidar com cada cliente conectado
def handle_client(client_socket, addr):
    print(f"[Servidor] Novo cliente conectado: {addr}")
    conexoes.append(client_socket)

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break  # Cliente desconectou
            print(f"[Servidor] Recebido de {addr}: {data.decode()}")
    except Exception as e:
        print(f"[Servidor] Erro com {addr}: {e}")
    finally:
        print(f"[Servidor] Cliente desconectado: {addr}")
        conexoes.remove(client_socket)
        client_socket.close()

# Função do servidor principal
def server(port=5000):
    host = get_local_ip()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"[Servidor] Aguardando conexões em {host}:{port}...")

    while True:
        client_sock, addr = server_socket.accept()
        client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
        client_thread.daemon = True
        client_thread.start()

# Função para enviar heartbeats a cada X segundos
def heartbeat_sender(interval=5):
    while True:
        time.sleep(interval)
        for conn in list(conexoes):  # Usa uma cópia para evitar problemas de concorrência
            try:
                conn.sendall(b"heartbeat\n")
            except Exception as e:
                print(f"[Servidor] Erro ao enviar heartbeat: {e}")
                conexoes.remove(conn)
                conn.close()

# Função para atuar como cliente (só para teste)
def client(target_host, target_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((target_host, target_port))
        threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

        while True:
            message = input("[Cliente] Digite uma mensagem (ou 'sair'): ")
            if message.lower() == 'sair':
                break
            sock.sendall(message.encode())

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if data:
                print(f"[Cliente] Recebido: {data.decode().strip()}")
        except:
            break

def get_local_ip():
    try:
        # Cria um socket UDP só para descobrir o IP (não envia nada)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 8.8.8.8 é só para descobrir a rota de saída
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Erro ao obter IP: {e}")
        return "127.0.0.1"

# Inicialização
if __name__ == "__main__":
    # Inicia o servidor em uma thread
    server_thread = threading.Thread(target=server, args=('localhost', 5000))
    server_thread.daemon = True
    server_thread.start()

    # Inicia o heartbeat em outra thread
    heartbeat_thread = threading.Thread(target=heartbeat_sender, args=(5,))
    heartbeat_thread.daemon = True
    heartbeat_thread.start()

    # Também atua como cliente para teste
    client(target_host='localhost', target_port=5000)
