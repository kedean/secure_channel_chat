import channel
import sys
import chat
from datetime import datetime
import time

class SecureChatController:
    __connection = None
    __ch = None
    __listener = None
    __chat_loop = None
    __port = 80
    
    def cleanup(self):
        if self.__chat_handler is not None:
            self.__chat_handler.close()
            self.__chat_handler = None
        if self.__connection is not None:
            self.__connection.close()
            self.__connection = None
        self.__listener = None
        self.__chat_loop = None
    
    def __init__(self, port, initial_screen_name=None, initial_connect_address=None, do_logging=False):
        self.__chat_handler = chat.Chat(log=do_logging)
        self.__chat_handler.init()
        self.__chat_handler.pushMessage("Listening for connections...")
        
        self.__connection = None
        self.__port = port
        
        if initial_connect_address is not None:
            self.__chat_handler.pushMessage("Attempting connection to {0}".format(initial_connect_address), refresh=True)
            
            self.__connection = channel.Client(initial_connect_address, port)
            result, result_code = self.__connection.connect() #this one isn't non-blocking, gotta wait!
            if result_code == -3: #connection refusal occurred
                self.__connection.close()
                self.__connection = channel.Listener(self.__port)
                self.__listener = self.__connection.listen()
                self.__chat_handler.pushMessage("The connection was refused!")
                self.__chat_handler.pushMessage("Listening for connections...", refresh=True)
            elif result_code == 0: #remote connection was made, we are a client!
                self.__chat_handler.pushMessage("Performing handshakes", refresh=True)
                self.__connection.doHandshakes()
                self.__chat_handler.pushMessage("Chat began on {0}".format(chat.Chat.dateString()), refresh=True)
                self.__chat_handler.setName(initial_screen_name if initial_screen_name is not None else "Client")
        else:
            self.__connection = channel.Listener(port)
            self.__listener = self.__connection.listen()
            
            self.__chat_handler.setName(initial_screen_name if initial_screen_name is not None else "Server")
        
        self.__chat_loop = self.__chat_handler.render()
    
    def __del__(self):
        self.cleanup()
    
    def renderLoop(self):
        if self.__chat_loop is not None:
            msg, code = self.__chat_loop.next()
            
            
            if self.__connection.connection_type is None: #no self.__connection establish yet, still listening
                
                result, result_code = self.__listener.next()
                
                if result_code == 0: #remote self.__connection was made, we are a server!
                    self.__chat_handler.pushMessage("Received connection from {0}".format(self.__connection.client_address[0]))
                    self.__chat_handler.pushMessage("Performing handshakes", refresh=True)
                    self.__connection.doHandshakes()
                    self.__chat_handler.pushMessage("Chat began on {0}".format(chat.Chat.dateString()), refresh=True)
            
            if code == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
                result, error = self.__connection.sendMessage("/quit")
                
                if self.__connection.connection_type == "server": #we need a response indicating the other party has quit already, or the next session may fail
                    timeout = time.time() + 5000 #maybe make variable?
                    while time.time() < timeout: #wait a maximum amount of time
                        result, error = self.__connection.receiveMessage()
                        if error != -2: #they said something (or lost self.__connection)! assume the protocol is valid and they said they're quitting too.
                            #print "Response was {0}".format(result)
                            break
                else:
                    pass #give no indication of acknowledement, just go
                    #self.__connection.sendMessage("/quit") #any message will work, so pick something simple here, just need to indicate we're closing down too
                self.cleanup()
                return (False, "Session ended.")
            elif code == 2:
                remote_address = msg
                
                self.__chat_handler.pushMessage("Attempting connection to {0}".format(remote_address), refresh=True)
                
                self.__connection.close() #we need to kill the server processing, we're now a client
                
                self.__connection = channel.Client(remote_address, self.__port)
                result, result_code = self.__connection.connect() #this one isn't non-blocking, gotta wait!
                if result_code == -3: #self.__connection refusal occurred
                    self.__connection.close()
                    self.__connection = channel.Listener(self.__port)
                    self.__listener = self.__connection.listen()
                    self.__chat_handler.pushMessage("The connection was refused!")
                    self.__chat_handler.pushMessage("Listening for connections...", refresh=True)
                elif result_code == 0: #remote self.__connection was made, we are a client!
                    self.__chat_handler.pushMessage("{0}...Connection established".format(self.__chat_handler.popMessage()))
                    self.__chat_handler.pushMessage("Performing handshakes", refresh=True)
                    self.__connection.doHandshakes()
                    
                    if self.__chat_handler.screen_name == "Server":
                        self.__chat_handler.setName("Client")
                    self.__chat_handler.pushMessage("Chat began on {0}".format(chat.Chat.dateString()), refresh=True)
            elif code == 1: #new screen name
                result, error = self.__connection.sendMessage("The other party is now known as {0}".format(msg))
                
                if error == -1: #problem!
                    self.cleanup()
                    return (False, "Connection was lost!")
                else: #success!
                    pass
            elif code == 0: #0 indicates a full messages is typed and ready to send
                #the messages sent are a tuple of (my_screen_name, time, text)
                #they are serialized internally
                
                result, error = self.__connection.sendMessage(msg)
                
                if error == -1: #problem!
                    self.cleanup()
                    return (False, "Connection was lost!")
                elif error == 0 : #success!
                    self.__chat_handler.pushMessage(msg)
            
            if self.__connection.connection_type is not None:
                #in either case we need to handle a possible receival
                result, error = self.__connection.receiveMessage()
                if error == -1:
                    self.cleanup()
                    return (False, "Connection was terminated by other party.")
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
                        self.__chat_handler.pushMessage(data, refresh=True)
                #a -2 error code means nothing has occured, so we'll go ahead and keep moving
            return (True, None)
        else:
            return (False, "No chat window.")
