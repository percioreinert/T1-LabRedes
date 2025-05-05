import cmd
import datetime
import hashlib
import socket
import threading
import uuid

from Print import Print

print_lock = threading.Lock()

CHUNK_SIZE = 1024
EOF_MARKER = b"<EOF>"

devices: list[Print] = []


class Interface(cmd.Cmd):
    intro = "Bem-vindo ao console interativo! Digite 'help' para ver os comandos.\n"
    prompt = ">>> "

    def __init__(self):
        super().__init__()
        self.port = 5007
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))  # Escuta na porta definida
        threading.Thread(target=self.listen_for_responses, daemon=True).start()  # Escuta por respostas

    def listen_for_responses(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            message = data.decode().strip()

            if message.startswith("[HEARTBEAT]"):
                node_name = message.split(' ')[1]
                sender_ip = addr[0]

                does_exist = False
                for device in devices:
                    if device.ip == sender_ip:
                        device.time = datetime.datetime.now()
                        does_exist = True

                if not does_exist:
                    devices.append(Print(sender_ip, node_name, datetime.datetime.now()))

    def do_devices(self, arg):
        if len(devices) == 0:
            print("Nenhum dispositivo encontrado.")
        else:
            for device in devices:
                print(f"Dispositivo: {device.name}, IP: {device.ip}, Tempo: {device.time}")

    def do_talk(self, arg):
        try:
            name, message = map(str, arg.split(' ', 1))
            target_ip = None

            # Encontrar o IP do dispositivo pelo nome
            for device in devices:
                if device.name == name:
                    target_ip = device.ip
                    break

            if target_ip:
                # prepara a mensagem gerando um uuid para esta mensagem
                message_uuid = uuid.uuid4()
                message_to_send = f"[TALK] {message_uuid} {message}"

                # Envia a mensagem
                self.sock.sendto(message_to_send.encode(), (target_ip, self.port))
                print(f"Mensagem enviada para {name} ({target_ip}): {message}")

                self.sock.settimeout(5)  # timeout para não ficar bloqueado eternamente esperando por uma resposta
                try:
                    # Espera a resposta de ACK
                    data, addr = self.sock.recvfrom(1024)
                    ack_message = data.decode().strip()

                    # se recebeu o ack com o uuid correto, a mensagem foi processada corretamente
                    if ack_message == f"[ACK] {message_uuid}":
                        print(f"Recebido ACK de {target_ip}: Mensagem processada com sucesso.")
                    else:
                        print(f"Recebido resposta inesperada de {target_ip}: {ack_message}")
                except socket.timeout:
                    print(f"Timeout! Nenhum ACK recebido de {target_ip} dentro do tempo esperado.")
            else:
                print(f"Dispositivo {name} não encontrado.")
        except ValueError:
            print("Uso incorreto. Tente: talk <nome_do_dispositivo> <mensagem>")

    def do_sendfile(self, arg):
        try:
            name, filepath = map(str, arg.split(' ', 1))  # Nome e a mensagem a ser enviada

            target_ip = None

            # Encontrar o IP do dispositivo pelo nome
            for device in devices:
                if device.name == name:
                    target_ip = device.ip
                    break

            if target_ip:
                with open(filepath, "rb") as file:

                    message_uuid = uuid.uuid4()
                    message_to_send = f"[FILE] {message_uuid} {filepath}"
                    self.sock.sendto(message_to_send.encode(), (target_ip, self.port))

                    self.sock.settimeout(5)  # timeout para não ficar bloqueado eternamente esperando por uma resposta
                    try:
                        # Espera a resposta de ACK
                        data, addr = self.sock.recvfrom(1024)
                        ack_message = data.decode().strip()

                        print(f"Resposta do [FILE]: {ack_message}")
                        # se recebeu o ack com o uuid correto, a mensagem foi processada corretamente
                        if ack_message == f"[ACK] {message_uuid} {filepath}":
                            print(f"Recebido ACK de {target_ip}: Envio do arquivo pode iniciar.")
                            seq = 0
                            while True:
                                chunk = file.read(CHUNK_SIZE)
                                if not chunk:
                                    break
                                # Adiciona número de sequência ao início
                                packet = f"[CHUNK] {seq:06d}".encode() + b"|" + chunk
                                self.sock.sendto(packet, (target_ip, self.port))
                                seq += 1
                        else:
                            print(f"Recebido resposta inesperada de {target_ip}: {ack_message}")
                    except socket.timeout:
                        print(f"Timeout! Nenhum ACK recebido de {target_ip} dentro do tempo esperado.")

                    file_hash = sha256_of_file("arquivo.txt")
                    message_to_send = f"[END] {message_uuid} {file_hash} arquivo_gerado.txt"

                    self.sock.sendto(message_to_send.encode(), (target_ip, self.port))

                    self.sock.settimeout(5)  # timeout para não ficar bloqueado eternamente esperando por uma resposta
                    try:
                        # Espera a resposta de ACK
                        data, addr = self.sock.recvfrom(1024)
                        ack_message = data.decode().strip()
                        print(ack_message)

                        # se recebeu o ack com o uuid correto, a mensagem foi processada corretamente
                        if ack_message == f"[ACK] {message_uuid}":
                            print("Arquivo enviado.")
                        elif ack_message == f"[NACK] {message_uuid} Hash Mismatch":
                            print("Hash mismatched")
                    except socket.timeout:
                        print(f"Timeout! Nenhum ACK recebido de {target_ip} dentro do tempo esperado.")
            else:
                print(f"Dispositivo {name} não encontrado.")
        except ValueError:
            print("Uso incorreto. Tente: sendfile <nome_do_dispositivo> <caminho_do_arquivo>")

    def do_leave(self, arg):
        print("Bye!")
        return True

    def do_EOF(self, arg):
        print("\nLeaving with Ctrl+D")
        return True


def sha256_of_file(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


if __name__ == "__main__":
    Interface().cmdloop()
