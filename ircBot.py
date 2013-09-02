#!/bin/python
"""
Create Connection________________
 |                               |
Listen for incoming messages    Wait for outgoing messages
 |
Process messages and commands
"""

import Queue
import socket
import threading
import time
import sched

class command():
    def __init__(self,minArgs,maxArgs,fun):
        self.minArgs = minArgs
        self.maxArgs = maxArgs
        self.fun = fun
    
    def __call__(self,botRef,caller,channel,params):
        if channel[0] != "#":   #if not in a channel (so if private)
            channel = caller    #Set channel to the caller for replyTo
        try:
            if params:
                if len(params) < self.minArgs:
                    raise Exception     #TODO exception
                if len(params) > self.maxArgs:
                    params[self.minArgs-1:] = [" ".join(params[self.minArgs-1:])]
                self.fun({"replyTo":channel,"user":caller},*params)
            else:
                self.fun({"replyTo":channel,"user":caller})
        except Exception as e:
            botRef.send("PRIVMSG",caller,"Error whilst executing the command") #TODO exception
            print e
    
    def help(self):
        if self.fun.__doc__ == "":
            raise NotImplementedError
        else:
            return self.fun.__doc__
    
            
class ircBot():
    def __init__(self,host,port,nick,password,autojoin=[]):
        self.host = host
        self.port = port
        self.nick = nick
        self.password = password
        self.autojoin = autojoin
        self.sendQueue = Queue.Queue()
        self.socket = socket.socket()
        self.recvThread = threading.Thread(target=ircBot._recvLoop,args=[self])
        self.recvThread.deamon = True
        self.sendThread = threading.Thread(target=ircBot._sendLoop,args=[self])
        self.sendThread.deamon = True
        self.commands = {}
        self.initCommands()
        self.scheduler = sched.scheduler(time.time,time.sleep)
                    
    def parseMessage(self,msg):
        prefix = ['','',''] #Prefix format: Nick/Server,User,Host
        
        #Parser assume /r/n has allready been removed
        if msg[0] == ":": #Check if message contains prefix
            i = msg.find(" ")
            if i == -1: raise ParsingError(msg,"Prefix Parsing","No space character after prefix")
            _prefix = msg[1:i] #Checking for a server name works the same as checking for a nick
                               #when being lazy, (assuming server name is correctlly formed)
                               #as it will not contain '!' or '@'
            msg = msg[i+1:].lstrip(" ")
            i = _prefix.find("!")
            j = _prefix.find("@")
            if i != -1 and j != -1: prefix = [_prefix[:i],_prefix[i+1:j],_prefix[j+1:]]
            elif i != -1: prefix = [_prefix[:i],_prefix[i+1:],'']
            elif j != -1: prefix = [_prefix[:j],'',_prefix[j+1:]]
            else: prefix = [_prefix,'','']
        i = msg.find(" ")
        if i == -1: raise ParsingError(msg,"Command Parsing","No space character after command")
        _command = msg[:i]
        if _command[0] >= "0" and _command[0] <= "9": #Command is numerical response code (have fun now)
            if len(_command) != 3: raise ParsingError(msg,"Command Parsing","Numeric code not 3 digits")
            try: command = int(_command)
            except ValueError: raise ParsingError(msg,"Command Parsing","Numeric code is not numeric")
        else: #Command is alpha
            for l in _command:
                if (l<"A")|(("Z"<l) & (l<"a"))|("z"<l): raise ParsingError(msg,"Command Parsing","Alpha Command '{0}' contains non-alphas '{1}'".format(_command,l))
            command = _command.upper()
        msg = msg[i+1:].lstrip(" ")
        params = []
        while len(msg) != 0:
            if msg[0] == ":": #Paramater is a trailing
                params.append(msg[1:])
                break
            else: #Paramater is non-trailing
                i = msg.find(" ")
                if i == -1: #Last paramater
                    params.append(msg)
                    break
                else:
                    params.append(msg[:i])
                    msg = msg[i+1:]
        return prefix,command,params
    
    def _sendLoop(self):
        while 1:
            message = self.sendQueue.get(True)
            if message == "#STOP#":
                break
            print "^^", message
            self.socket.sendall(message)
            self.sendQueue.task_done()
    
    def _recvLoop(self):
        try:
            while 1:
                buff= ""
                while (buff[-2:] != "\r\n"):
                    buff = buff + self.socket.recv(1024)
                for message in buff.split("\r\n"):
                    if message == "": continue
                    prefix,command,params = self.parseMessage(message)
                    if command == "PING":
                        self.send("PONG",*params)
                    elif command == "PRIVMSG":
                        print params[0],"|",prefix[0],">",params[1]
                        if params[1][0] == ".": #TODO magic character
                            try:
                                botCmd,botParams = params[1][1:].split(" ",1)
                                botParams = botParams.split(" ")
                            except ValueError:
                                botCmd = params[1][1:].lower()
                                botParams = [].lower()
                            try:
                                cmd = self.commands[botCmd](self,prefix[1],params[0],botParams)
                            except KeyError:
                                self.send("PRIVMSG",prefix[1],"Command {0} not found, try .help for a list of commands".format(cotCmd)) #TODO magic character
                            else:
                                try:
                                    cmd(self,prefix[1],params[0],botParams)
                                except:
                                    #Error whilst executing command
                    elif command == 42:
                        self.onConnected()
                    elif command == 900:
                        self.onLoggedin()   #todo move ns login back here.
                    else:
                        print prefix,command,params #DEBUG
                    #TODO handle nick changes ect."""
        except socket.timeout:
            print "Connection timed out on recv"
            self.sendQueue.put("#STOP#")
            
    
    def send(self,command,*params):
        if len(params) > 0:
            message = command+" "+" ".join(params[:-1])+" :"+params[-1]+"\r\n"
        else:
            message = command+"\r\n"
        self.sendQueue.put(message)
    
    def connect(self):
        self.socket.connect((self.host,self.port))
        self.send("NICK",self.nick)
        self.send("USER","pythonIrcBot","BunnyBaseSystem","PythonIRCBot","?","Sailor (v3)")
        self.socket.settimeout(5*60) #Timeout set to 5 minuets
        self.recvThread.start()
        self.sendThread.start()
    
    def onConnected(self):
        self.send("PRIVMSG","nickserv","identify "+self.password)
        self.send("JOIN",",".join(self.autojoin))
    
    def initCommands(self):
        self.commands = {
            "help":command(0,1,self.helpCommand)
        }

    def onLoggedin(self):
        pass
        
    def helpCommand(self,cmdInfo,cmd=None):
        if cmd is None:
            self.send("PRIVMSG",cmdInfo["replyTo"],"The following commands are accepted: {0}".format(" ".join(["."+c for c in self.commands,keys()]))) #TODO magic character
            self.send("PRIVMSG",cmdInfo["replyTo"],"Use .help [command] for more info on each one")
        else:
            if cmd[0] == ".":   #TODO magic character
                cmd = cmd[1:]
            cmd = cmd.lower()
            try:
                self.send("PRIVMSG",cmdInfo["replyTo"],self.commands[cmd].help())
            except KeyError:
                self.send("PRIVMSG",cmdInfo["replyTo"],"Command {0} not found, try .help for a list of commands".format(cmd)) #TODO magic character
            except NotImplementedError:
                self.send("PRIVMSG",cmdInfo["replyTo"],"No help for the {0} command found.")
