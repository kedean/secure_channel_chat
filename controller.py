import channel
import sys
import chat
from datetime import datetime
import time

class SecureChatController:
    _connection = None
    _ch = None
    _listener = None
    _chat_loop = None
    _port = 80
    
    def cleanup(self):
        if self._chat_handler is not None:
            self._chat_handler.close()
            self._chat_handler = None
        if self._connection is not None:
            self._connection.close()
            self._connection = None
        self._listener = None
        self._chat_loop = None
    
    def __init__(self, port, initial_screen_name=None, initial_connect_address=None, do_logging=False):
        self._chat_handler = chat.Chat(log=do_logging)
        self._chat_handler.init()
        self._chat_handler.pushMessage("Listening for connections...")
        
        self._connection = None
        self._port = port
        
        if initial_connect_address is not None:
            self._chat_handler.pushMessage("Attempting connection to {0}".format(initial_connect_address), refresh=True)
            
            self._connection = channel.Client(initial_connect_address, port)
            result, result_code = self._connection.connect() #this one isn't non-blocking, gotta wait!
            if result_code == -3: #connection refusal occurred
                self._connection.close()
                self._connection = channel.Listener(self._port)
                self._listener = self._connection.listen()
                self._chat_handler.pushMessage("The connection was refused!")
                self._chat_handler.pushMessage("Listening for connections...", refresh=True)
            elif result_code == 0: #remote connection was made, we are a client!
                self._chat_handler.pushMessage("Performing handshakes", refresh=True)
                self._connection.doHandshakes()
                now = datetime.now()
                self._chat_handler.pushMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute), refresh=True)
                self._chat_handler.setName(initial_screen_name if initial_screen_name is not None else "Client")
        else:
            self._connection = channel.Listener(port)
            self._listener = self._connection.listen()
            
            self._chat_handler.setName(initial_screen_name if initial_screen_name is not None else "Server")
        
        self._chat_loop = self._chat_handler.render()
    
    def __del__(self):
        self.cleanup()
    
    def renderLoop(self):
        msg, code = self._chat_loop.next()
        
        if self._connection.connection_type is None: #no self._connection establish yet, still listening
            result, result_code = self._listener.next()
            
            if result_code == 0: #remote self._connection was made, we are a server!
                now = datetime.now()
                self._chat_handler.pushMessage("Received connection from {0}".format(self._connection.client_address[0]))
                self._chat_handler.pushMessage("Performing handshakes", refresh=True)
                self._connection.doHandshakes()
                self._chat_handler.pushMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute), refresh=True)
        
        if code == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
            result, error = self._connection.sendMessage("/quit")
            
            if self._connection.connection_type == "server": #we need a response indicating the other party has quit already, or the next session may fail
                timeout = time.time() + 5000 #maybe make variable?
                while time.time() < timeout: #wait a maximum amount of time
                    result, error = self._connection.receiveMessage()
                    if error != -2: #they said something (or lost self._connection)! assume the protocol is valid and they said they're quitting too.
                        #print "Response was {0}".format(result)
                        break
            else:
                self._connection.sendMessage("/quit") #any message will work, so pick something simple here, just need to indicate we're closing down too
            self.cleanup()
            return (False, "Session ended.")
        elif code == 2:
            remote_address = msg
            
            self._chat_handler.pushMessage("Attempting connection to {0}".format(remote_address), refresh=True)
            
            self._connection.close() #we need to kill the server processing, we're now a client
            
            self._connection = channel.Client(remote_address, self._port)
            result, result_code = self._connection.connect() #this one isn't non-blocking, gotta wait!
            if result_code == -3: #self._connection refusal occurred
                self._connection.close()
                self._connection = channel.Listener(self._port)
                self._listener = self._connection.listen()
                self._chat_handler.pushMessage("The connection was refused!")
                self._chat_handler.pushMessage("Listening for connections...", refresh=True)
            elif result_code == 0: #remote self._connection was made, we are a client!
                self._chat_handler.pushMessage("{0}...Connection established".format(self._chat_handler.popMessage()))
                self._chat_handler.pushMessage("Performing handshakes", refresh=True)
                self._connection.doHandshakes()
                
                if self._chat_handler.screen_name == "Server":
                    self._chat_handler.setName("Client")
                now = datetime.now()
                self._chat_handler.pushMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute), refresh=True)
        elif code == 1: #new screen name
            result, error = self._connection.sendMessage("The other party is now known as {0}".format(msg))
            
            if error == -1: #problem!
                self.cleanup()
                return (False, "Connection was lost!")
            else: #success!
                pass
        elif code == 0: #0 indicates a full messages is typed and ready to send
            #the messages sent are a tuple of (my_screen_name, time, text)
            #they are serialized internally
            
            result, error = self._connection.sendMessage(msg)
            
            if error == -1: #problem!
                self.cleanup()
                return (False, "Connection was lost!")
            elif error == 0 : #success!
                self._chat_handler.pushMessage(msg)
        
        if self._connection.connection_type is not None:
            #in either case we need to handle a possible receival
            result, error = self._connection.receiveMessage()
            if error == -1:
                self.cleanup()
                return (False, "\nConnection was terminated by other party.")
            elif error == -4: #bad authentication
                self.cleanup()
                return (False, "Message contained a bad authenticator, a message was lost in transit or someone is modifying your communications, halting.")
            elif error == 0: #got a real message!
                #using the previous definition, unpack the message received
                data = result
                if data == "/quit": #quit sequence, the other party ended their session.
                    self.cleanup()
                    return (False, "Connection was terminated by the other party.")
                else:
                    self._chat_handler.pushMessage(data, refresh=True)
            #a -2 error code means nothing has occured, so we'll go ahead and keep moving
        return (True, None)
