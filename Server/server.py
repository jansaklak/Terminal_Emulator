import socket
import threading
import pty
import os
import select
import subprocess
import struct
import fcntl
import termios

HOST = '0.0.0.0'
PORT = 5000

def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def handle_client(conn, addr):
    print(f"[POŁĄCZENIE] {addr}")
    
    master_fd, slave_fd = pty.openpty()
    set_winsize(master_fd, 24, 100)
    
    shell = subprocess.Popen(
        [
            "docker", "run", "--rm", "-it",
            "--network", "lab-net",
            "--memory=128m",
            "--cpus=0.5",
            "mysql:8.0",
            "mysql",
            "-h", "mysql",
            "-u", "labuser",
            "-plabpass",
            "labdb"
        ],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
    )

    def read_from_pty():
        try:
            while True:
                r, _, _ = select.select([master_fd], [], [], 0.05)
                if r:
                    output = os.read(master_fd, 4096).decode('utf-8', errors='ignore')
                    if output:
                        conn.sendall(output.encode('utf-8'))
        except: pass

    threading.Thread(target=read_from_pty, daemon=True).start()

    try:
    # Rozpoczęcie nasłuchu od klienta.
    while True:

        data = conn.recv(1024).decode('utf-8')
        # Jeśli dane są puste - klient zamknął połączenie.
        if not data: break
        
        # Sprawdzenie, czy otrzymano naciśnięcie TAB.
        if data.startswith("TAB_REQ:"):
            # Wycięcie prefiksu polecenia, który użytkownik zaczął wpisywać.
            prefix = data.split(":", 1)[1]
            # \x15 to Ctrl+U (czyści linię), potem wpisujemy prefix i wysyłamy dwa tabulatory (\t\t).
            os.write(master_fd, b"\x15" + prefix.encode() + b"\t\t")
            
        elif data == "__SIGINT__":
            os.write(master_fd, b"\x03")
            
        else:
            # Przekazujemy komende - dodajemy enter.
            os.write(master_fd, (data + "\n").encode())

    finally:
        # Zamknięcie głównego deskryptora wirtualnego terminala (PTY).
        os.close(master_fd)
        # Zamknięcie pomocniczego deskryptora terminala.
        os.close(slave_fd)
        # Zamknięcie połączenia sieciowego z klientem.
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()