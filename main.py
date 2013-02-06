import channel
import sys
import chat
import pickle

if __name__ == '__main__':
    #is server
    defport = 8000
    
    ch = chat.Chat()
    
    connection = None
    
    if "-server" in sys.argv:
        connection = channel.Listener(defport)
        print "Waiting for connection."
        connection.listen()
        ch.setName("Server")
    elif "-client" in sys.argv:
        print "Attempting connection."
        addr = "127.0.0.1"
        for arg in sys.argv:
            if "-" not in arg:
                addr = arg
        if addr is not None:
            connection = channel.Client(addr, defport)
            connection.connect()
        else:
            print "Invalid address!"
            exit(-3)
        
        ch.setName("Client")
            
    for msg in ch.render():
        if msg == -2: #-2 indicates the user typed the 'quit' command sequence, send an indication to the other party and exit
            ch.close()
            print "\nTerminating connection."
            text_to_send = pickle.dumps("/quit")
            result, error = connection.sendMessage(text_to_send)
            exit(0)
        elif msg != -1: #strict -1 means that the user is still typing their message, otherwise they have hit return and the message should be sent to the other party
            #the messages sent are a pickled tuple of (my_screen_name, text), later this should be encrypted
            text_to_send = pickle.dumps(msg)
            result, error = connection.sendMessage(text_to_send)
            if error == -1: #problem!
                ch.close()
                print "\nConnection was lost!"
                exit(-1)
            else: #success!
                pass
        
        #in either case we need to handle a possible receival
        result, error = connection.receiveMessage()
        if error == -1:
            ch.close()
            print "{0}: {1}".format(error, result)
            exit(-2)
        elif error == 0: #got a real message!
            #using the previous definition, unpack the message received
            data = pickle.loads(result)
            
            if data == "/quit": #quit sequence, the other party ended their session.
                ch.close()
                print "\nConnection was terminated by other party."
                exit(0)
            else:
                ch.addMessage(data)
        #a -2 error code means nothing has occured, so we'll go ahead and keep moving
