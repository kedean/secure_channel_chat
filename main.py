import channel
import sys
import chat
import pickle
from datetime import datetime
import time

if __name__ == '__main__':
    
    port = 8000
    
    #parse out arguments
    found_arg = None
    initial_connect_address = None
    initial_screen_name = None
    
    for arg in sys.argv:
        if found_arg is not None:
            if found_arg == "address" or found_arg == "a":
                initial_connect_address = arg
                found_arg = None
            elif found_arg == "port" or found_arg == "p":
                try:
                    port = int(arg)
                except:
                    print("Port must be an integer value.")
                    exit(-1)
            elif found_arg == "name" or found_arg == "n":
                initial_screen_name = arg
        elif arg[0] == "-":
            found_arg = arg[1:]
            
    
    #create but DO NOT YET initialize the chat window, this way error and results can still be posted first
    ch = chat.Chat()
    ch.addMessage("Listening for connections...")
    
    #connection = None
    
    #begin in server mode, if the user tries to connect to an ip then later switch to client mode
    
    connection = None
    if initial_connect_address is not None:
        ch.addMessage("Attempting connection to {0}".format(initial_connect_address))
        
        connection = channel.Client(initial_connect_address, port)
        result, result_code = connection.connect() #this one isn't non-blocking, gotta wait!
        if result_code == -3: #connection refusal occurred
            ch.close()
            connection.close()
            print(result)
            exit(-3)
        elif result_code == 0: #remote connection was made, we are a client!
            now = datetime.now()
            ch.addMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute))
        
        ch.setName(initial_screen_name if initial_screen_name is not None else "Client")
    else:
        connection = channel.Listener(port)
        listener = connection.listen()
        
        ch.setName(initial_screen_name if initial_screen_name is not None else "Server")
    
    #initialize the chat box and start running
    
    for msg, code in ch.render():
        
        if connection.connection_type is None: #no connection establish yet, still listening
            result, result_code = listener.next()
            
            if result_code == 0: #remote connection was made, we are a server!
                now = datetime.now()
                ch.addMessage("Received connection from {0}".format(connection.client_address[0]))
                ch.addMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute))
                ch.refreshQueue()
        
        if code == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
            ch.close()
            print("\nTerminating connection.")
            
            text_to_send = pickle.dumps("/quit")
            result, error = connection.sendMessage(text_to_send)
            
            if connection.connection_type == "server": #we need a response indicating the other party has quit already, or the next session may fail
                timeout = time.time() + 5000 #maybe make variable?
                while time.time() < timeout: #wait a maximum amount of time
                    result, error = connection.receiveMessage()
                    if error != -2: #they said something (or lost connection)! assume the protocol is valid and they said they're quitting too.
                        #print "Response was {0}".format(result)
                        break
            else:
                connection.sendMessage("/quit") #any message will work, so pick something simple here, just need to indicate we're closing down too
            connection.close()
            exit(0)
        elif code == 2:
            remote_address = msg
            connection.close() #we need to kill the server processing, we're now a client
            ch.addMessage("Attempting connection to {0}".format(remote_address))
            ch.refreshQueue()
            connection = channel.Client(remote_address, port)
            result, result_code = connection.connect() #this one isn't non-blocking, gotta wait!
            if result_code == -3: #connection refusal occurred
                ch.close()
                connection.close()
                print(result)
                exit(-3)
            elif result_code == 0: #remote connection was made, we are a client!
                if ch.screen_name == "Server":
                    ch.setName("Client")
                now = datetime.now()
                ch.addMessage("Chat began on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year, now.month, now.day,  now.hour, now.minute))
                ch.refreshQueue()
        elif code == 1: #new screen name
            result, error = connection.sendMessage(pickle.dumps("The other party is now known as {0}".format(msg)))
            
            if error == -1: #problem!
                ch.close()
                connection.close()
                print("\nConnection was lost!")
                exit(-1)
            else: #success!
                pass
        elif code == 0: #0 indicates a full messages is typed and ready to send
            #the messages sent are a pickled tuple of (my_screen_name, text), later this should be encrypted
            text_to_send = pickle.dumps(msg)
            result, error = connection.sendMessage(text_to_send)
            
            if error == -1: #problem!
                ch.close()
                connection.close()
                print("\nConnection was lost!")
                exit(-1)
            elif error == 0 : #success!
                ch.addMessage(msg)
        
        if connection.connection_type is not None:
            #in either case we need to handle a possible receival
            result, error = connection.receiveMessage()
            if error == -1:
                ch.close()
                connection.close()
                print("{0}: {1}".format(error, result))
                exit(-2)
            elif error == 0: #got a real message!
                #using the previous definition, unpack the message received
                data = pickle.loads(result)
                
                if data == "/quit": #quit sequence, the other party ended their session.
                    ch.close()
                    connection.close()
                    print("\nConnection was terminated by other party.")
                    exit(0)
                else:
                    ch.addMessage(data)
                    ch.refreshQueue()
            #a -2 error code means nothing has occured, so we'll go ahead and keep moving
        
        time.sleep(0.01)
