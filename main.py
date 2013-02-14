import sys
import time

import controller

if __name__ == '__main__':
    
    port = 8000
    
    #parse out arguments
    found_arg = None
    initial_connect_address = None
    initial_screen_name = None
    do_logging = "-log" in sys.argv
    
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
            
    
    control = controller.SecureChatController(port, initial_screen_name, initial_connect_address, do_logging)
    while control.renderLoop():
        time.sleep(0.01)
