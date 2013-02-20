import socket
import sys

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import random
from Crypto.Cipher import AES
from Crypto.Util import Counter
from Crypto.Hash import SHA256
from Crypto.Hash import HMAC

import base64

import numpy

class SecureChannel(object):
    
    NO_CONNECTION = None
    SERVER, CLIENT = 1, 2
    
    
    socket = None
    address = None
    port = 8000
    connection, client_address = None, None
    __buffer_size = 4096
    _role = None
    
    __rsa_key = None
    __rsa_keylength = 2048
    __rsa_other_pubkey = None
    __rsa_cipher = None
    __rsa_othercipher = None
    
    __shared_key = None
    __encrypt_cipher = None
    __decrypt_cipher = None
    
    __num_msg_sent = 0
    __num_msg_recv = 0
    
    __standard_salt = "i am a message salt!"
    
    def __constant_time_equality(self, a, b):
        assert len(a) == len(b)
        return sum([int(l1 != l2) for l1, l2 in zip(a, b)]) == 0
    
    def __init__(self, address, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address, self.port = address, port
        self._role = self.NO_CONNECTION
    def __del__(self):
        self.close()
    
    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self._role = self.NO_CONNECTION
    
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
                
        
        try:
            if self.__encrypt_cipher is not None:
                og = message
                message = base64.b64encode(self.__encrypt_cipher.encrypt(message))
                
                authenticator_hasher = HMAC.new(self.__auth_send_hmac, digestmod=SHA256.new())
                authenticator_hasher.update(message)
                authenticator_hasher.update(str(self.__num_msg_sent))
                authenticator = authenticator_hasher.hexdigest()
                message = "{0}{1}".format(authenticator, message)
                self.__num_msg_sent += 1
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
        if self.connection is None or self._role is None:
            return ("No connection exists.", -3)
        try:
            data = self.connection.recv(self.__buffer_size)
            if data is not None and len(data) > 0:
                if self.__decrypt_cipher is not None:
                    authenticator, data = data[0:64], data[64:] #the first half of any post-handshake message will be a 64-byte hex string of the authenticator, then the rest is the message
                    reauthentication_hasher = HMAC.new(self.__auth_recv_hmac, digestmod=SHA256.new())
                    reauthentication_hasher.update(data)
                    reauthentication_hasher.update(str(self.__num_msg_recv))
                    reauthenticator = reauthentication_hasher.hexdigest()
                    
                    if not self.__constant_time_equality(authenticator, reauthenticator):
                        return ("Authentication of message failed.", -4)
                    
                    self.__num_msg_recv += 1
                    
                    data = self.__decrypt_cipher.decrypt(base64.b64decode(data))
                    
                    if "\x02" in data: #the data was a list of message components, reconstruct the list as the return value
                        #note that this should only happen during chat transport, when the decryption cipher is valid
                        #\x02 bytes could appear during key exchange as well, which we do not want to alter, so this transform
                        #only occurs when the encryption system is fully functioning and set up
                        data = data.split("\x02")
                    with open("x.txt", "w") as log:
                        log.write(str(len(data)) + "\n")
                return (data, 0)
            else:
                return ("No connection.", -1)
        except Exception:
            return ("No data recieved.", -2)
    
    #custom version of receiveMessage that simply blocks until it gets a non-empty message. All true errors (!= -2) are still returned.
    def receiveMessageBlocking(self):
        message, error = None, -2
        while error == -2:
            message, error = self.receiveMessage()
        return (message, error)
    
    def __intToBytes(self, val, num_bytes):
        return bytearray([(val & (0xff << pos*8)) >> pos*8 for pos in range(num_bytes)])
    
    def __startHandshake(self, passphrase):
        """
        self.__rsa_key = RSA.generate(self.__rsa_keylength)
        self.__rsa_cipher = PKCS1_OAEP.new(self.__rsa_key)
        pem = self.__rsa_key.exportKey()
        self.sendMessage(pem)
        
        result, error = self.receiveMessageBlocking()
        if error != 0:
            return error
        self.__rsa_other_pubkey = RSA.importKey(result)
        self.__rsa_othercipher = PKCS1_OAEP.new(self.__rsa_other_pubkey)
        
        exp1 = random.getrandbits(256)
        
        msg_crypt = self.__rsa_othercipher.encrypt(str(exp1))
        self.sendMessage(base64.b64encode(msg_crypt))
        
        exp2 = None
        
        result, error = self.receiveMessageBlocking()
        if error != 0:
            return error
        msg = base64.b64decode(result)
        try:
            exp2 = long(self.__rsa_cipher.decrypt(msg))
        except Exception as e:
            exit()
        
        self.__shared_key = buffer(self.__intToBytes(exp1 ^ exp2, 256 / 8))
        return 0
        """
        
        key_exchange_cipher = AES.new(passphrase, AES.MODE_CTR, counter=Counter.new(128))
        
        exp1 = random.getrandbits(256)
        
        msg_crypt = key_exchange_cipher.encrypt(str(exp1))
        self.sendMessage(base64.b64encode(msg_crypt))
        
        exp2 = None
        
        result, error = self.receiveMessageBlocking()
        if error == -1:
            return -3 #a -1 (disconnection) error indicates that the other party did not accept the key, so it is cast to -3 (bad key)
        elif error != 0:
            return error
        msg = base64.b64decode(result)
        try:
            exp2 = long(key_exchange_cipher.decrypt(msg))
        except Exception as e:
            return -3
        
        self.__shared_key = buffer(self.__intToBytes(exp1 ^ exp2, 256 / 8))
        return 0
    
    def __acceptHandshake(self, passphrase):
        """result, error = self.receiveMessageBlocking()
        
        if error != 0:
            return error
        self.__rsa_other_pubkey = RSA.importKey(result)
        self.__rsa_othercipher = PKCS1_OAEP.new(self.__rsa_other_pubkey)
        
        self.__rsa_key = RSA.generate(self.__rsa_keylength)
        self.__rsa_cipher = PKCS1_OAEP.new(self.__rsa_key)
        self.sendMessage(self.__rsa_key.exportKey())
        
        exp1 = None
        result, error = self.receiveMessageBlocking()
        if error != 0:
            return error
        msg = base64.b64decode(result)
        try:
            exp1 = long(self.__rsa_cipher.decrypt(msg))
        except Exception as e:
            exit("could not decrypt")
        
        exp2 = random.getrandbits(256)
        msg_crypt = self.__rsa_othercipher.encrypt(str(exp2))
        self.sendMessage(base64.b64encode(msg_crypt))
        
        self.__shared_key = buffer(self.__intToBytes(exp1 ^ exp2, 256 / 8))
        
        return 0
        """
        key_exchange_cipher = AES.new(passphrase, AES.MODE_CTR, counter=Counter.new(128))
        
        exp1 = None
        result, error = self.receiveMessageBlocking()
        if error != 0:
            return error
        msg = base64.b64decode(result)
        try:
            exp1 = long(key_exchange_cipher.decrypt(msg))
        except Exception as e:
            return -3
        
        exp2 = random.getrandbits(256)
        msg_crypt = key_exchange_cipher.encrypt(str(exp2))
        error = self.sendMessage(base64.b64encode(msg_crypt))
        if error == -1:
            return -2 #a -1 (disconnection) error indicates that the other party did not accept the key, so it is cast to -2 (bad key)
        
        self.__shared_key = buffer(self.__intToBytes(exp1 ^ exp2, 256 / 8))
        
        return 0
        
    def __initSecureChannel(self):
        
        """
        keys are generated for the four possible encryption/decryption situations
        if the user is a server (conn_type != client), then they are ordered slightly differently
        """
        enc_send_key, enc_recv_key, self.__auth_send_hmac, self.__auth_recv_hmac = [
            SHA256.new(str(self.__shared_key) + uniq_text).digest()
            for uniq_text in (["a send b", "b send a", "a auth b", "b auth a"] if self._role == self.CLIENT else ["b send a", "a send b", "b auth a", "a auth b"])
        ]
        
        #in the case of send/recv encryption, we only need one cipher, rather than making a new one each time.
        self.__encrypt_cipher = AES.new(enc_send_key, AES.MODE_CTR, counter=Counter.new(128))
        self.__decrypt_cipher = AES.new(enc_recv_key, AES.MODE_CTR, counter=Counter.new(128))
        
        return 0
    
    def doHandshakes(self, withPassphrase=None):
        ret = 0
        passphrase = SHA256.new(self.__standard_salt + str(withPassphrase)).digest()
        if self._role == self.SERVER:
            ret = self.__startHandshake(passphrase)
        else:
            ret = self.__acceptHandshake(passphrase)
        
        if ret != 0:
            return ret
        else:
            return self.__initSecureChannel()
        
    
    @property
    def connection_type(self): #should be refactored to be DRY-er
        return {
            self.NO_CONNECTION: None,
            self.SERVER: 'server',
            self.CLIENT: 'client'
        }.get(self._role, None)

class Listener(SecureChannel):
    
    def __init__(self, port):
        SecureChannel.__init__(self, "", port)
    
    def listen(self):
        while self.connection_type is self.NO_CONNECTION:
            
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
                
                self._role = self.SERVER
                
                yield ("Success.", 0)
            except socket.error:
                yield ("Address is already in use or port is unusable.", -3) #make more informative
    def listen_non_blocking(self):
        pass
    
class Client(SecureChannel):
    
    def __init__(self, address, port):
        SecureChannel.__init__(self, address, port)
    
    def connect(self):
        try:
            self.socket.connect((self.address, self.port))
            self.connection = self.socket
            self.connection.setblocking(0)
            self._role = self.CLIENT
            
            return ("Success.", 0)
        except socket.error:
            return ("The connection was refused or failed!", -3) #make more informative
