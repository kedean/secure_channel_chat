import terminal
import sys
import curses
import os
from datetime import datetime

class Chat:
    _has_rendered = False
    
    def __init__(self, screen_name="_"):
        self.message_queue = []
        self.screen_name = screen_name
        
    def __del__(self):
        self.close()
    def close(self):
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
        termsize = terminal.getTerminalSize()
        subqueue = self.message_queue
    
        if len(self.message_queue) > termsize[1] - 2:
            subqueue = self.message_queue[0 - (termsize[1] - 2):]
        
        for y in range(0, termsize[1] - 2):
            try:
                timestamp = " on {0}-{1}-{2} at {3:02d}:{4}".format(subqueue[y][1].year,
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
        self.refreshQueue()
    
    def render(self):
        if not self._has_rendered:
            self.init()
        
        while True:
            
            self.refreshQueue()
            
            termsize = terminal.getTerminalSize()
            
            msg = []
            cursor = 0
            
            self.stdscr.addstr(termsize[1]-1, 0, "Message: " + (" " * (termsize[0] - 1 - len("Message: "))))
            self.stdscr.move(termsize[1] - 1, len("Message: "))
            
            while True:
                c = self.stdscr.getch()
                if c != -1:
                    if c == 10:
                        break
                    elif c == 127 and cursor > 0:
                        del msg[cursor - 1]
                        cursor -= 1
                        self.stdscr.move(termsize[1]-1, 0)
                        self.stdscr.clrtoeol()
                        self.stdscr.addstr(termsize[1]-1, 0, "Message: " + "".join(msg))
                    elif c >= 32 and c <= 126:
                        self.stdscr.move(termsize[1]-1, 0)
                        self.stdscr.clrtoeol()
                        msg.insert(cursor, chr(c))
                        self.stdscr.addstr(termsize[1]-1, 0, "Message: " + "".join(msg))
                        
                        cursor += 1
                    elif c == curses.KEY_LEFT: #left control sequence
                        if cursor >= 0:
                            cursor -= 1
                    elif c == curses.KEY_RIGHT: #right
                        if cursor < len(msg):
                            cursor += 1
                    else:
                        pass
                        
                self.stdscr.move(termsize[1] - 1, len("Message: ") + cursor) #this needs to be done every time, or else the cursor will be shifted when messages are received
                    
                yield -1
            
            out_msg = "".join(msg)
            
            if out_msg[0] == "/": #forward slash at the start of a message indicates a command sequence, do not add it to the queue, only yield back the corresponding code
                if out_msg == "/quit":
                    yield -2
            else:
                out_tuple = (self.screen_name, datetime.now(), out_msg)
                self.addMessage(out_tuple)
                yield out_tuple
        
        return
    def shouldRefresh(self):
        return True
