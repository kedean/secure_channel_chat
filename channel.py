import socket
import sys

class Channel:
    socket = None
    address = None
    port = 8000
    connection, client_address = None, None
    buffer_size = 4096
    connection_type = None
    
    def __init__(self, address, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address, self.port = address, port
    def __del__(self):
        self.close()
    
    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
    
    def sendMessage(self, message):
        if self.connection is None:
            return ("No connection.", -2)
        try:
            self.connection.send(message)
            return ("Success.", 0)
        except Exception:
            return ("An exception occurred in transport.", -1)
    def receiveMessage(self):
        if self.connection is None or self.connection_type is None:
            return ("No connection exists.", -3)
        try:
            data = self.connection.recv(self.buffer_size)
            if data:
                return (data, 0)
            else:
                return ("No connection.", -1)
        except Exception:
            return ("No data recieved.", -2)

class Listener(Channel):
    
    def __init__(self, port):
        Channel.__init__(self, "localhost", port)
    
    def listen(self):
        while self.connection_type is None:
            try:
                self.socket.bind((self.address, self.port))
                self.socket.listen(1)
                self.socket.setblocking(0)
                while self.connection is None:
                    try:
                        self.connection, self.client_address = self.socket.accept()
                        break
                    except:
                        yield ("No connection made.", -1)
                self.connection.setblocking(0)
                self.connection_type = "server"
                yield ("Success.", 0)
            except socket.error:
                yield ("Address is already in use or port is unusable.", -3) #make more informative
    def listen_non_blocking(self):
        pass
    
class Client(Channel):
    
    def __init__(self, address, port):
        Channel.__init__(self, address, port)
    
    def connect(self):
        try:
            self.socket.connect((self.address, self.port))
            self.connection = self.socket
            self.connection.setblocking(0)
            self.connection_type = "client"
            return ("Success.", 0)
        except socket.error:
            return ("The connection was refused or failed!", -3) #make more informative
    
    
