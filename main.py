import sys
import time
import argparse
from controller import *

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="A decentralized chat client implementing a secure channel for communications.")
    parser.add_argument("-a", "--address", default=None, dest="initial_connect_address", help="Address to connect to on startup. If left blank, a broadcast is started.")
    parser.add_argument("-p", "--port", default=8000, dest="port", help="The port number to open and broadcast connections on.", type=int) 
    parser.add_argument("-n", "--nick", default=None, dest="initial_screen_name", help="Screen name to be given on startup.")
    parser.add_argument("--log", dest="do_logging", action="store_true")
    args = parser.parse_args()
    
    FRAMESLEEP = 0.01
    
    try:
        control = SecureChatController(args.port, args.initial_screen_name, args.initial_connect_address, args.do_logging)
        control_running, control_return = True, None
        while control_running:
            control_running, control_return = control.renderLoop()
            time.sleep(FRAMESLEEP)
            
        print control_return
    except Exception as e:
        print sys.exc_info()
        with open('log.txt', 'w') as log:
            log.write(str(sys.exc_info()) + '\n')

