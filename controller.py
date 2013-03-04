#primary classes
from chat import *
from channel import *

#supporting libs
import sys
from datetime import datetime
import time

class SecureChatController:
    __connection = None
    __ch = None
    __listener = None
    __chat_loop = None
    __port = 80
    __waiting_for_passphrase = False
    __connect_to_address = None
    __is_stale = False
    
    def cleanup(self):
        if self.__chat_handler is not None:
            self.__chat_handler.close()
            self.__chat_handler = None
        if self.__connection is not None:
            self.__connection.close()
            self.__connection = None
        self.__listener = None
        self.__chat_loop = None
        self.__is_stale = True
    
    def __init__(self, port, initial_screen_name=None, initial_connect_address=None, do_logging=False):
        self.__chat_handler = Chat(log=do_logging)
        self.__chat_handler.init()
        
        self.__port = port
        
        self.__connect_to_address = initial_connect_address
        
        self.__eventConnectionAsListener()
        
        if initial_screen_name is None:
            self.__chat_handler.setName("_", suppressMessage=True)
        else:
            self.__chat_handler.setName(initial_screen_name, suppressMessage=True)
        
        self.__chat_loop = self.__chat_handler.render()
    
    def __del__(self):
        self.cleanup()
    
    def renderLoop(self):
        if self.__is_stale:
            return (False, "The chat controller has gone stale.")
        
        elif self.__chat_loop is not None:
            retval = (True, None)
            
            msg, code = self.__chat_loop.next()
            
            if self.__connection.connection_type is None: #no self.__connection establish yet, still listening
                retval = self.__eventTryListener()
                if retval[0] == False:
                    self.cleanup()
                    return retval
            
            if self.__connect_to_address is not None:
                addr = self.__connect_to_address
                self.__connect_to_address = None
                retval = self.__eventConnectionAsClient(addr)
                if retval[0] == False:
                    self.cleanup()
                    return retval
            
            if code == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
                retval = self.__eventQueuedQuit()
                if retval[0] == False:
                    self.cleanup()
                    return retval
            elif code == 2:
                retval = self.__eventConnectionAsClient(msg)
                if retval[0] == False:
                    self.cleanup()
                    return retval
            elif code == 1: #new screen name
                result, error = self.__connection.sendMessage("The other party is now known as {0}".format(msg))
                
                if error == -1: #problem!
                    self.cleanup()
                    return (False, "Connection was lost!")
            elif code == 0: #0 indicates a full messages is typed and ready to send
                
                if self.__waiting_for_passphrase: #the current message is treated as the users passphrase, collected and used for trading keys
                    retval = self.__eventQueuedPassphrase(msg)
                    if retval[0] == False:
                        self.__chat_handler.pushMessage(retval[1], refresh=True)
                        retval = self.__eventConnectionAsListener()
                        if retval[0] == False:
                            self.cleanup()
                            return retval
                else:
                    retval = self.__eventQueuedMessage(msg)
                    if retval[0] == False:
                        self.__chat_handler.pushMessage(retval[1], refresh=True)
                        retval = self.__eventConnectionAsListener()
                        if retval[0] == False:
                            self.cleanup()
                            return retval
            
            if self.__connection.connection_type is not None and not self.__waiting_for_passphrase:
                retval = self.__eventTryReceivingMessage(msg)
                if retval[0] == False:
                    self.__chat_handler.pushMessage(retval[1], refresh=True)
                    retval = self.__eventConnectionAsListener()
                    if retval[0] == False:
                        self.cleanup()
                        return retval
            
            #a -2 error code means nothing has occured, so we'll go ahead and keep moving
            return retval
        else:
            self.cleanup()
            return (False, "No chat window.")
    
    def __eventConnectionAsListener(self):
        self.__connection = Listener(self.__port)
        self.__listener = self.__connection.listen()
        self.__chat_handler.pushMessage("Listening for connections...", refresh=True)
        
        return (True, None)
        
    def __eventConnectionAsClient(self, remote_address):
        self.__chat_handler.pushMessage("Attempting connection to {0}".format(remote_address), refresh=True)
        
        self.__connection.close() #we need to kill the server processing, we're now a client
        
        self.__connection = Client(remote_address, self.__port)
        result, result_code = self.__connection.connect() #this one isn't non-blocking, gotta wait!
        if result_code == -3: #self.__connection refusal occurred
            self.__connection.close()
            self.__chat_handler.pushMessage("The connection was refused!")
            
            return self.__eventConnectionAsListener()
        elif result_code == 0: #remote self.__connection was made, we are a client!
            self.__chat_handler.pushMessage("{0}...Connection established".format(self.__chat_handler.popMessage()))
            self.__chat_handler.pushMessage("Please enter your shared passphrase.", refresh=True)
            self.__waiting_for_passphrase = True
            self.__chat_handler.startStealthMode()
        
        return (True, None)
    
    def __eventTryListener(self):
        result, result_code = self.__listener.next()
        
        if result_code == 0: #remote self.__connection was made, we are a server!
            self.__chat_handler.pushMessage("Received connection from {0}".format(self.__connection.client_address[0]))
            self.__chat_handler.pushMessage("Please enter your shared passphrase.", refresh=True)
            self.__waiting_for_passphrase = True
            self.__chat_handler.startStealthMode()
        
        return (True, None)
    
    def __eventQueuedPassphrase(self, phrase):
        phrase = phrase[2]
        self.__chat_handler.stopStealthMode()
        self.__chat_handler.pushMessage("Waiting for other party and performing handshakes", refresh=True)
        error = self.__connection.doHandshakes(phrase)
        if error == -3: #the parties entered different passwords
            return (False, "The passphrases did not match.")
        elif error != 0:
            return (False, "{0}: Something went wrong with your handshake.".format(error))
        
        other_sn = None
        
        if self.__chat_handler.screen_name == "_":
            if self.__connection.connection_type == "client":
                self.__chat_handler.setName("Client")
            else: #implied server
                self.__chat_handler.setName("Server")
            self.__chat_handler.pushMessage("Use '/nick newname' to change your nickname.", refresh=True)
        
        if self.__connection.connection_type == "client":
            #the client initiates name exchange
            self.__connection.sendMessage(self.__chat_handler.screen_name)
            other_sn, error = self.__connection.receiveMessageBlocking()
            if error != 0:
                return (False, error)
        else:
            other_sn, error = self.__connection.receiveMessageBlocking()
            if error != 0:
                return (False, error)
            self.__connection.sendMessage(self.__chat_handler.screen_name)
        
        self.__chat_handler.pushMessage("Chat with {0} began on {1}".format(other_sn, Chat.dateString()), refresh=True)
        
        self.__waiting_for_passphrase = False
        
        return (True, None)
    
    def __eventQueuedMessage(self, msg):
        #the messages sent are a tuple of (my_screen_name, time, text)
        #they are serialized internally
        
        result, error = self.__connection.sendMessage(msg)
        
        if error == -1: #problem!
            return (False, "Connection was lost!")
        elif error == 0 : #success!
            self.__chat_handler.pushMessage(msg)
        
        return (True, None)
    
    def __eventTryReceivingMessage(self, msg):
        #in either case we need to handle a possible receival
        result, error = self.__connection.receiveMessage()
        if error == -1:
            return (False, "Connection was terminated by other party.")
        elif error == -4: #bad authentication
            return (False, "Message contained a bad authenticator, a message was lost in transit or someone is modifying your communications, halting.")
        elif error == 0: #got a real message!
            #using the previous definition, unpack the message received
            data = result
            
            if data == Chat.MSG_QUIT: #quit sequence, the other party ended their session.
                return (False, "Connection was terminated by the other party.")
            else:
                self.__chat_handler.pushMessage(data, refresh=True)
        return (True, None)
    
    def __eventQueuedQuit(self):
        result, error = self.__connection.sendMessage(Chat.MSG_QUIT)
        
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
        return (False, "Session ended.")
    
    
    
