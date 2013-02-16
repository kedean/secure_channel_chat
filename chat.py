import sys
import curses
import os
from datetime import datetime

class Chat:
    __has_rendered = False
    __log_file = None
    
    def __init__(self, screen_name="_", init=False, log=False):
        self.message_queue = []
        self.screen_name = screen_name
        if log:
            if os.path.exists("logs/") == False:
                os.mkdir("logs/")
            filename = "logs/log_{0}.txt".format(datetime.now())
            log_file = open(filename, "w")
            self.__log_file = log_file
        if init:
            self.init()
        
    def __del__(self):
        self.close()
    def close(self):
        if self.__log_file is not None:
            self.__log_file.close()
            self.__log_file = None
        if self.__has_rendered:
            curses.endwin()
            #os.system("clear")
            self.__has_rendered = False
            
    
    def init(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        self.stdscr.keypad(1)
        self.stdscr.leaveok(0)
        self.stdscr.nodelay(1)
        self.__has_rendered = True
        
    def setName(self, name):
        self.screen_name = name
    
    def refreshQueue(self):
        termsize = self.stdscr.getmaxyx()
        subqueue = self.message_queue
        
        if len(self.message_queue) > termsize[0] - 2:
            subqueue = self.message_queue[0 - (termsize[0] - 2):]
        
        for y in range(0, termsize[0] - 2):
            try:
                plaintext = subqueue[y]
                if not isinstance(subqueue[y], str): #for messages where the queue item is a string, just display that (like system notices), otherwise parse like usual
                    plaintext = subqueue[y][0] + " on " + subqueue[y][1] + ": " + subqueue[y][2] #currently items are tuples of (screen_name, msg)
                self.stdscr.addstr(y, 0, plaintext)
            except IndexError:
                pass
        
        self.stdscr.refresh()
    
    def pushMessage(self, msg, refresh=False):
        if isinstance(msg, str) or ((isinstance(msg, tuple) or isinstance(msg, list)) and len(msg) == 3 and isinstance(msg[0], str) and isinstance(msg[1], str) and isinstance(msg[2], str)):
            self.message_queue.append(msg)
            if self.__log_file is not None:
                for msg in self.message_queue:
                    plaintext = msg
                    if not isinstance(msg, str): #for messages where the queue item is a string, just display that (like system notices), otherwise parse like usual
                        plaintext = msg[0] + " on " + msg[1] + ": " + msg[2]
                    self.__log_file.write(plaintext + "\n")
        else:
            raise TypeError("Chat messages must be either a string or a 3-tuple of strings (in format (username, timestamp, text)).")
        
        if refresh:
            self.refreshQueue()
        
    def popMessage(self, refresh=False):
        item = self.message_queue.pop(-1)
        if refresh:
            self.refreshQueue()
        return item
    
    def render(self):
        if not self.__has_rendered:
            self.init()
        
        while True:
            
            self.refreshQueue()
            
            termsize = self.stdscr.getmaxyx()
            
            msg = [] #set up as an array of characters so that insertion/deletion is easy (backspace/delete/etc)
            cursor = 0
            
            self.stdscr.addstr(termsize[0]-1, 0, "Message: " + (" " * (termsize[1] - 1 - len("Message: "))))
            self.stdscr.move(termsize[0] - 1, len("Message: "))
            
            while True:
                c = self.stdscr.getch()
                if c != -1:
                    if c == 10:
                        break
                    elif c == 127 and cursor > 0:
                        del msg[cursor - 1]
                        cursor -= 1
                        self.stdscr.move(termsize[0]-1, 0)
                        self.stdscr.clrtoeol()
                        self.stdscr.addstr(termsize[0]-1, 0, "Message: " + "".join(msg))
                    elif c >= 32 and c <= 126:
                        self.stdscr.move(termsize[0]-1, 0)
                        self.stdscr.clrtoeol()
                        msg.insert(cursor, chr(c))
                        self.stdscr.addstr(termsize[0]-1, 0, "Message: " + "".join(msg))
                        
                        cursor += 1
                    elif c == curses.KEY_LEFT: #left control sequence
                        if cursor >= 0:
                            cursor -= 1
                    elif c == curses.KEY_RIGHT: #right
                        if cursor < len(msg):
                            cursor += 1
                    else:
                        pass
                        
                self.stdscr.move(termsize[0] - 1, len("Message: ") + cursor) #this needs to be done every time, or else the cursor will be shifted when messages are received
                    
                yield ("character checked.", -1)
            
            out_msg = "".join(msg)
            
            if out_msg[0] == "/": #forward slash at the start of a message indicates a command sequence, do not add it to the queue, only yield back the corresponding code
                if out_msg == "/quit":
                    yield ("quitting", -2)
                elif out_msg[0:len("/name ")] == "/name ":
                    self.setName(out_msg[len("/name "):])
                    self.pushMessage("You are now known as '{0}'".format(self.screen_name))
                    #add a 'getLastMesage' so that the parent code can extract the last message on a certain return code and send it to the other party, such as this message (though modified)
                    yield (self.screen_name, 1)
                elif out_msg[0:len("/connect ")] == "/connect ":
                    yield (out_msg[len("/connect "):], 2)
            else:
                now = datetime.now()
                timestamp = "{0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(now.year,
                                                                                    now.month,
                                                                                    now.day,
                                                                                    now.hour,
                                                                                    now.minute
                                                                                    )
                out_tuple = (self.screen_name, timestamp, out_msg)
                yield (out_tuple, 0)
        
        return
    def shouldRefresh(self):
        return True
