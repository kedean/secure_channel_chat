import sys
import curses
import os
from datetime import datetime

class Chat:
    __has_rendered = False
    __log_file = None
    __typed_message_queue = [] #a queue of everything typed into the message box (only inserted after a return, plus whatever was last typed)
    __typed_message_pointer = 0
    __stealth_mode = False
    __msg = []
    
    def startStealthMode(self):
        self.__stealth_mode = True
        self.__msg = []
        self.refreshQueue(refreshMessage=True)
    
    def stopStealthMode(self):
        self.__stealth_mode = False
        self.__msg = []
        self.refreshQueue(refreshMessage=True)
    
    def __init__(self, screen_name="_", init=False, log=False):
        self.message_queue = []
        self.screen_name = screen_name
        if log:
            self.startLogging(suppressMessage=True)
        if init:
            self.init()
        
    def __del__(self):
        self.close()
    
    def close(self):
        self.stopLogging(suppressMessage=True)
        if self.__has_rendered:
            curses.endwin()
            #os.system("clear")
            self.__has_rendered = False
            
    def startLogging(self, directory='logs', suppressMessage=False):
        directory = '{0}/'.format(directory)
        if os.path.exists(directory) == False:
            os.mkdir(directory)
        filename = "{0}/log_{1}.txt".format(directory, datetime.now())
        log_file = open(filename, "w")
        self.__log_file = log_file
        self.pushMessage("Logging is now enabled.")
    
    def stopLogging(self, suppressMessage=False):
        self.pushMessage("Logging is now disabled.")
        if self.__log_file is not None:
            self.__log_file.close()
            self.__log_file = None
    
    def init(self):
        self.stdscr = curses.initscr()
        curses.noecho()
        self.stdscr.keypad(1)
        self.stdscr.leaveok(0)
        self.stdscr.nodelay(1)
        self.__has_rendered = True
        
    def setName(self, name, suppressMessage=False):
        self.screen_name = name
        if not suppressMessage:
            self.pushMessage("You are now known as '{0}'".format(self.screen_name))
    
    def refreshQueue(self, refreshMessage=False):
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
        
        if refreshMessage:
            self.stdscr.move(termsize[0]-1, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(termsize[0]-1, 0, self.prompt)
        
        self.stdscr.refresh()
    
    def pushMessage(self, msg, refresh=False):
        if isinstance(msg, str) or ((isinstance(msg, tuple) or isinstance(msg, list)) and len(msg) == 3 and isinstance(msg[0], str) and isinstance(msg[1], str) and isinstance(msg[2], str)):
            self.message_queue.append(msg)
            if self.__log_file is not None:
                #for msg in self.message_queue:
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
    
    @property
    def prompt(self):
        return ("Message: " if not self.__stealth_mode else "Passphrase: ")
    
    def render(self):
        if not self.__has_rendered:
            self.init()
        
        while True:
            
            self.refreshQueue()
            
            termsize = self.stdscr.getmaxyx()
            
            self.__msg = [] #set up as an array of characters so that insertion/deletion is easy (backspace/delete/etc)
            cursor = 0
            
            self.stdscr.move(termsize[0]-1, 0)
            self.stdscr.clrtoeol()
            self.stdscr.addstr(termsize[0] - 1, 0, self.prompt)
            self.stdscr.move(termsize[0] - 1, len(self.prompt))
            
            while True:
                c = self.stdscr.getch()
                if c != -1:
                    if c == 10:
                        if not self.__stealth_mode:
                            if self.__typed_message_pointer + 1 < len(self.__typed_message_queue):
                                self.__typed_message_queue.pop(-1)
                                
                            self.__typed_message_queue.append(self.__msg)
                            self.__typed_message_pointer = len(self.__typed_message_queue) - 1
                        
                        #since the return has occured, we need to cull the old message from the chat line
                        self.stdscr.move(termsize[0]-1, 0)
                        self.stdscr.clrtoeol()
                        self.stdscr.addstr(termsize[0]-1, 0, self.prompt)
                        break
                    elif c == 127 and cursor > 0:
                        del self.__msg[cursor - 1]
                        cursor -= 1
                        self.stdscr.move(termsize[0]-1, 0)
                        self.stdscr.clrtoeol()
                        if self.__stealth_mode:
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join("*" * len(self.__msg)))
                        else:
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join(self.__msg))
                    elif c >= 32 and c <= 126:
                        self.stdscr.move(termsize[0]-1, 0)
                        self.stdscr.clrtoeol()
                        self.__msg.insert(cursor, chr(c))
                        if self.__stealth_mode:
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join('*' * len(self.__msg)))
                        else:
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join(self.__msg))
                        
                        cursor += 1
                    elif c == curses.KEY_LEFT: #left control sequence
                        if cursor >= 0:
                            cursor -= 1
                    elif c == curses.KEY_RIGHT: #right
                        if cursor < len(self.__msg):
                            cursor += 1
                    elif c == curses.KEY_UP and not self.__stealth_mode:
                        if self.__typed_message_pointer >= 0:
                            if self.__typed_message_pointer + 1 == len(self.__typed_message_queue):
                                self.__typed_message_queue.append(self.__msg)
                            self.__msg = self.__typed_message_queue[self.__typed_message_pointer]
                            self.stdscr.move(termsize[0]-1, 0)
                            self.stdscr.clrtoeol()
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join(self.__msg))
                            cursor = len(self.__msg)
                            self.__typed_message_pointer -= 1
                    elif c == curses.KEY_DOWN and not self.__stealth_mode:
                        if self.__typed_message_pointer + 1 < len(self.__typed_message_queue):
                            self.__typed_message_pointer += 1
                            self.__msg = self.__typed_message_queue[self.__typed_message_pointer]
                            self.stdscr.move(termsize[0]-1, 0)
                            self.stdscr.clrtoeol()
                            self.stdscr.addstr(termsize[0]-1, 0, self.prompt + "".join(self.__msg))
                            cursor = len(self.__msg)
                    else:
                        pass
                        
                self.stdscr.move(termsize[0] - 1, len(self.prompt) + cursor) #this needs to be done every time, or else the cursor will be shifted when messages are received
                    
                yield ("character checked.", -1)
            
            out_msg = "".join(self.__msg)
            
            if out_msg[0] == "/": #forward slash at the start of a message indicates a command sequence, do not add it to the queue, only yield back the corresponding code
                if out_msg == Chat.MSG_QUIT:
                    yield ("quitting", -2)
                elif out_msg[0:len(Chat.MSG_NAME_CHANGE)] == Chat.MSG_NAME_CHANGE:
                    self.setName(out_msg[len(Chat.MSG_NAME_CHANGE):])
                    #add a 'getLastMesage' so that the parent code can extract the last message on a certain return code and send it to the other party, such as this message (though modified)
                    yield (self.screen_name, 1)
                elif out_msg[0:len(Chat.MSG_CONNECT)] == Chat.MSG_CONNECT:
                    yield (out_msg[len(Chat.MSG_CONNECT):], 2)
                elif out_msg == Chat.MSG_START_LOGGING:
                    self.startLogging()
                    yield ("began logging", 3)
                elif out_msg == Chat.MSG_STOP_LOGGING:
                    self.stopLogging()
                    yield ("stopped logging", 4)
                elif out_msg == Chat.MSG_HELP:
                    self.pushMessage("Available Commands:\nQuit: {0}\nChange Username: {1}new_name\nConnect to server: {2}server_name\nEnable logging: {3}\nDisable Logging: {4}".format(
                        Chat.MSG_QUIT,
                        Chat.MSG_NAME_CHANGE,
                        Chat.MSG_CONNECT,
                        Chat.MSG_START_LOGGING,
                        Chat.MSG_STOP_LOGGING
                        )
                    )
                    yield ("showed help", 5)
                else:
                    self.pushMessage("Command sequence {0} is unknown. Type {1} for a list of commands.".format(out_msg, Chat.MSG_HELP))
                    yield ("unkown command", 6)
            else:
                out_tuple = (self.screen_name, self.dateString(), out_msg)
                yield (out_tuple, 0)
        
        return
    
    @staticmethod
    def dateString(d=None):
        if not isinstance(d, datetime):
            d = datetime.now()
        
        timestamp = "{0:02d}-{1:02d}-{2:02d} at {3:02d}:{4:02d}".format(d.year,
                                                                        d.month,
                                                                        d.day,
                                                                        d.hour,
                                                                        d.minute
                                                                        )
        return timestamp
    
    MSG_QUIT = "/quit"
    MSG_NAME_CHANGE = "/nick "
    MSG_CONNECT = "/connect "
    MSG_START_LOGGING = "/enable logging"
    MSG_STOP_LOGGING = "/disable logging"
    MSG_HELP = "/help"
