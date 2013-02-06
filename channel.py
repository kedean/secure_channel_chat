import socket
import sys

class Channel:
    socket = None
    address = None
    port = 8000
    connection, client_address = None, None
    buffer_size = 4096
    
    def __init__(self, address, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address, self.port = address, port
    def __del__(self):
        self.close()
    
    def close(self):
        if self.socket is not None:
            self.socket.close()
        if self.connection is not None:
            self.connection.close()
    
    def sendMessage(self, message):
        if self.connection is None:
            return ("No connection.", -1)
        try:
            self.connection.send(message)
            return ("Success.", 0)
        except Exception:
            return ("An exception occurred in transport.", -1)
    def receiveMessage(self):
        if self.connection is None:
            return ("No connection exists.", -1)
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
        try:
            self.socket.bind((self.address, self.port))
            self.socket.listen(1)
            self.connection, self.client_address = self.socket.accept()
            self.connection.setblocking(0)
        except socket.error:
            print "Address is already in use or port is unusable." #make more informative
            exit(-1)
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
        except socket.error:
            print "The connection was refused or failed!" #make more informative
            exit(-1)
    
    
