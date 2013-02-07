import sys
import curses
import os
from datetime import datetime

class Chat:
    _has_rendered = False
    _log_file = None
    
    def __init__(self, screen_name="_", init=False, log=False):
        self.message_queue = []
        self.screen_name = screen_name
        if log:
            if os.path.exists("logs/") == False:
                os.mkdir("logs/")
            filename = "logs/log_{0}.txt".format(datetime.now())
            log_file = open(filename, "w")
            self._log_file = log_file
        if init:
            self.init()
        
    def __del__(self):
        self.close()
    def close(self):
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
        if self._has_rendered:
            curses.endwin()
            #os.system("clear")
            self._has_rendered = False
            
    
    def init(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        self.stdscr.keypad(1)
        self.stdscr.leaveok(0)
        self.stdscr.nodelay(1)
        self._has_rendered = True
        
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
                    #need better error checking
                    timestamp = " on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(subqueue[y][1].year,
                                                                    subqueue[y][1].month,
                                                                    subqueue[y][1].day,
                                                                    subqueue[y][1].hour,
                                                                    subqueue[y][1].minute
                                                                    )
                    plaintext = subqueue[y][0] + timestamp + ": " + subqueue[y][2] #currently items are tuples of (screen_name, msg)
                self.stdscr.addstr(y, 0, plaintext)
            except IndexError:
                pass
    
    def addMessage(self, msg):
        self.message_queue.append(msg)
        if self._log_file is not None:
            for msg in self.message_queue:
                plaintext = msg
                if not isinstance(msg, str): #for messages where the queue item is a string, just display that (like system notices), otherwise parse like usual
                    timestamp = " on {0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(
                        msg[1].year,
                        msg[1].month,
                        msg[1].day,
                        msg[1].hour,
                        msg[1].minute
                        )
                    plaintext = msg[0] + timestamp + ": " + msg[2]
                self._log_file.write(plaintext + "\n")
        
    
    def render(self):
        if not self._has_rendered:
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
                    self.addMessage("You are now known as '{0}'".format(self.screen_name))
                    #add a 'getLastMesage' so that the parent code can extract the last message on a certain return code and send it to the other party, such as this message (though modified)
                    yield (self.screen_name, 1)
                elif out_msg[0:len("/connect ")] == "/connect ":
                    yield (out_msg[len("/connect "):], 2)
            else:
                out_tuple = (self.screen_name, datetime.now(), out_msg)
                yield (out_tuple, 0)
        
        return
    def shouldRefresh(self):
        return True
