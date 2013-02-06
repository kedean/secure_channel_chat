import channel
import sys
import chat
import pickle
from datetime import datetime
import time

if __name__ == '__main__':
    
    port = 8000
    remote_address = "127.0.0.1"
    
    #parse out arguments
    found_arg = None
    is_server = False
    is_client = False
    
    for arg in sys.argv:
        if found_arg is not None:
            if found_arg == "address" or found_arg == "a":
                remote_address = arg
                found_arg = None
            elif found_arg == "port" or found_arg == "p":
                try:
                    port = int(arg)
                except:
                    print "Port must be an integer value."
                    exit(-1)
        elif arg[0] == "-":
            if arg == "-server" or arg == "-s":
                is_server = True #note that being a server takes precedence over being a client, eventually they should be equivalent and multiple connection should be allowed
            elif arg == "-client" or arg == "-c":
                is_client = True
            else:
                found_arg = arg[1:]
            
    
    #create but DO NOT YET initialize the chat window, this way error and results can still be posted first
    ch = chat.Chat()
    
    connection = None
    
    #make requisite connections to parties
    if is_server:
        connection = channel.Listener(port)
        print "Waiting for connection."
        result, result_code = connection.listen()
        if result_code == -3:
            print result
            exit(-3)
        ch.setName("Server")
    elif is_client:
        print "Attempting connection."
        
        if remote_address is None:
            print "Invalid address!"
            exit(-3)
        
        connection = channel.Client(remote_address, port)
        result, result_code = connection.connect()
        
        if result_code == -3:
            print result
            exit(-3)
        
        ch.setName("Client")
    
    #initialize the chat box and start running
    
    now = datetime.now()
    ch.addMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute))
    
    for msg in ch.render():
        if msg == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
            ch.close()
            print "\nTerminating connection."
            
            text_to_send = pickle.dumps("/quit")
            result, error = connection.sendMessage(text_to_send)
            
            if is_server: #we need a response indicating the other party has quit already, or the next session may fail
                timeout = time.time() + 5000 #maybe make variable?
                while time.time() < timeout: #wait a maximum amount of time
                    result, error = connection.receiveMessage()
                    if error != -2: #they said something (or lost connection)! assume the protocol is valid and they said they're quitting too.
                        print "Response was {0}".format(result)
                        break
            else:
                connection.sendMessage("/quit") #any message will work, so pick something simple here, just need to indicate we're closing down too
            connection.close()
            exit(0)
        elif msg != -1: #strict -1 means that the user is still typing their message, otherwise they have hit return and the message should be sent to the other party
            #the messages sent are a pickled tuple of (my_screen_name, text), later this should be encrypted
            text_to_send = pickle.dumps(msg)
            result, error = connection.sendMessage(text_to_send)
            
            if error == -1: #problem!
                ch.close()
                connection.close()
                print "\nConnection was lost!"
                exit(-1)
            else: #success!
                pass
        
        #in either case we need to handle a possible receival
        result, error = connection.receiveMessage()
        if error == -1:
            ch.close()
            connection.close()
            print "{0}: {1}".format(error, result)
            exit(-2)
        elif error == 0: #got a real message!
            #using the previous definition, unpack the message received
            data = pickle.loads(result)
            
            if data == "/quit": #quit sequence, the other party ended their session.
                ch.close()
                connection.close()
                print "\nConnection was terminated by other party."
                exit(0)
            else:
                ch.addMessage(data)
                ch.refreshQueue()
        #a -2 error code means nothing has occured, so we'll go ahead and keep moving
