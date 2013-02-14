import socket
import sys

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import random
from Crypto.Cipher import AES
from Crypto.Util import Counter

import base64

import numpy

class Channel:
    socket = None
    address = None
    port = 8000
    connection, client_address = None, None
    buffer_size = 4096
    connection_type = None
    
    _rsa_key = None
    _rsa_keylength = 2048
    _rsa_other_pubkey = None
    _rsa_cipher = None
    _rsa_othercipher = None
    
    _shared_key = None
    _encrypt_cipher = None
    _decrypt_cipher = None
    
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
        
        if not isinstance(message, str): #regular strings should go straight to the encoding/transfer process
            try:
                message_list = list(message) #cast, if this fails it was a bad argument
            except:
                return ("Message must be either a string or an iterable of strings.")
            else:
                """
                the hex byte \x02, or the ascii 'start of text', is used for concatenating message components, so it cannot occur in any
                of the components. It is assumed it does not, but is stripped out in case. The protocol may mess up message that contain this
                byte for some reason.
                
                the caveat in message reception does not concern this portion, as key transfer will never involve iterables
                """
                message_list = [item.strip("\x02") for item in message_list]
                message = "\x02".join(message_list)
                
        
        with open("log.txt", "a") as log:
            log.write("d\n")
        
        try:
            if self._encrypt_cipher is not None:
                message = base64.b64encode(self._encrypt_cipher.encrypt(message))
        except:
            return ("An exception occurred in encryption.", -3)
        else:
            try:
                self.connection.send(message)
            except Exception:
                return ("An exception occurred in transport.", -1)
            else:
                return ("Success.", 0)
        
    def receiveMessage(self):
        if self.connection is None or self.connection_type is None:
            return ("No connection exists.", -3)
        try:
            data = self.connection.recv(self.buffer_size)
            if data:
                if self._decrypt_cipher is not None:
                    
                    data = self._decrypt_cipher.decrypt(base64.b64decode(data))
                    
                    if "\x02" in data: #the data was a list of message components, reconstruct the list as the return value
                        #note that this should only happen during chat transport, when the decryption cipher is valid
                        #\x02 bytes could appear during key exchange as well, which we do not want to alter, so this transform
                        #only occurs when the encryption system is fully functioning and set up
                        data = data.split("\x02")
                return (data, 0)
            else:
                return ("No connection.", -1)
        except Exception:
            return ("No data recieved.", -2)
    
    def _int_to_bytes(self, val, num_bytes):
        return bytearray([(val & (0xff << pos*8)) >> pos*8 for pos in range(num_bytes)])
    
    def _startHandshake(self):
        self._rsa_key = RSA.generate(self._rsa_keylength)
        self._rsa_cipher = PKCS1_OAEP.new(self._rsa_key)
        pem = self._rsa_key.exportKey()
        self.sendMessage(pem)
        while self._rsa_other_pubkey is None:
            result, error = self.receiveMessage()
            
            if error == -1:
                return -1
            elif error == 0: #response
                self._rsa_other_pubkey = RSA.importKey(result)
                self._rsa_othercipher = PKCS1_OAEP.new(self._rsa_other_pubkey)
        
        exp1 = random.getrandbits(256)
        
        msg_crypt = self._rsa_othercipher.encrypt(str(exp1))
        self.sendMessage(base64.b64encode(msg_crypt))
        
        exp2 = None
        while exp2 is None:
            result, error = self.receiveMessage()
            
            if error == -1:
                return -1
            elif error == 0: #response
                msg = base64.b64decode(result)
                try:
                    exp2 = long(self._rsa_cipher.decrypt(msg))
                except Exception as e:
                    exit("could not decrypt")
        
        self._shared_key = buffer(self._int_to_bytes(exp1 ^ exp2, 256 / 8))
        
    
    def _acceptHandshake(self):
        while self._rsa_other_pubkey is None:
            result, error = self.receiveMessage()
            
            if error == -1:
                return -1
            elif error == 0: #response
                self._rsa_other_pubkey = RSA.importKey(result)
                self._rsa_othercipher = PKCS1_OAEP.new(self._rsa_other_pubkey)
        
        self._rsa_key = RSA.generate(self._rsa_keylength)
        self._rsa_cipher = PKCS1_OAEP.new(self._rsa_key)
        self.sendMessage(self._rsa_key.exportKey())
        
        exp1 = None
        while exp1 is None:
            result, error = self.receiveMessage()
            
            if error == -1:
                return -1
            elif error == 0: #response
                msg = base64.b64decode(result)
                try:
                    exp1 = long(self._rsa_cipher.decrypt(msg))
                except Exception as e:
                    exit("could not decrypt")
        
        exp2 = random.getrandbits(256)
        msg_crypt = self._rsa_othercipher.encrypt(str(exp2))
        self.sendMessage(base64.b64encode(msg_crypt))
        
        self._shared_key = buffer(self._int_to_bytes(exp1 ^ exp2, 256 / 8))
        
    def _initSecureChannel(self):
        ctr = Counter.new(128)
        self._encrypt_cipher = AES.new(self._shared_key, AES.MODE_CTR, counter=ctr)
        self._decrypt_cipher = AES.new(self._shared_key, AES.MODE_CTR, counter=ctr)
    
    def doHandshakes(self):
        if self.connection_type == "server":
            self._startHandshake()
        else:
            self._acceptHandshake()
        
        self._initSecureChannel()

class Listener(Channel):
    
    def __init__(self, port):
        Channel.__init__(self, "", port)
    
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
