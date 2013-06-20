#!/usr/bin/python

from ircBot import *
import urllib
from sgmllib import SGMLParser
from datetime import datetime

PASSWORD = open("pswd").read() #To avoid it ending up on github ;)

#TODO replace parser
class meetParser(SGMLParser):
    def __init__(self,botRef):
        self.botRef = botRef
        SGMLParser.__init__(self)
        
    def reset(self):
        SGMLParser.reset(self)
        self.inItem = False
        self.inTag = ""
        self.current = meetInfo()
        self.botRef.upComingMeets = []
        
    def unknown_starttag(self,tag,attr):
        if tag == "item":
            self.inItem = True
        else:
            self.inTag = tag
    
    def unknown_endtag(self,tag):
        if tag == "item":
            self.botRef.upComingMeets.append(self.current)
            self.current = meetInfo()
    
    def handle_data(self,data):
        data = data.strip()
        if self.inItem and data:
            if self.inTag == "pubdate":
                self.current.datetime = datetime.strptime(data[:-6],"%a, %d %b %Y %H:%M:%S")
            elif self.inTag == "title":
                self.current.title = data
            elif self.inTag == "link":
                self.link = data
            elif self.inTag == "description":
                self.description = data
   
class meetInfo():
    def __init__(self):
        self.datetime = None
        #self.location = None #Lacking data
        self.title = None
        self.description = None
        self.link = None
        
    def __str__(self):
        return "{title}: {description} ({link})".format(title=self.title,description=self.description,link=self.link)

class capIzzy(ircBot):
    def __init__(self):
        ircBot.__init__(self)
        self.upComingMeets=[]
        
    def onConnected(self):
        self.send("PRIVMSG","nickserv","identify CaptainIzzy "+PASSWORD)
        self.send("JOIN","#bristolbronies")
    
    def onLoggedin(self):
        self.updateMeetinfo()

    def initCommands(self):
        self.commands = {
            "meets":command(0,0,self.getUpcomingMeets)
            #"navigation":command(2,2,self.navigateToMeet) #Unimplmented RSS feed lacks location data
        }
    
    def getUpcomingMeets(self,cmdInfo):
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here are the next few upcoming meets, for help getting to them use the Navigate command: .navigate [start location] [meet no]")
        for i,m in enumerate(upComingMeets):
            self.send("PRIVMSG",cmdInfo["replyTo"],"[#{0}] {1}".format(i,m))
 
    def navigateToMeet(self,cmdInfo,startPoint,goalMeet):
        meetLocation = urllib.quote_plus(upcomingMeets[goalMeet].location)
        meetDate = urllib.quote_plus(upcomingMeets[goalMeet].datetime.strftime("%d/%m/%y"))
        meetTime = urllib.quote_plus(upcomingMeets[goalMeet].datetime.strftime("%H:%M"))
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here you go, this should help get you here. https://maps.google.co.uk/maps?ttype=arr&dirflg=r&saddr={start}&daddr={meetLocation}&date={date}&time={time}".format(start=startPoint,meetLocation=meetLocation,date=meetDate,time=meetTime))
        
    def updateMeetinfo(self): #TODO multithread?
        parser = meetParser(self)
        feed = urllib.urlopen("http://bristolbronies.co.uk/meet/feed/")
        parser.feed(feed.read())
        feed.close()
        parser.close()
        self.upComingMeets.sort(lambda a,b:(a.datetime-b.datetime).days)
        if len(self.upComingMeets) > 1:
            self.send("TOPIC","#bristolbronies","Next upcoming Bristol Bronies meet:{nextMeet}. For more upcoming meets type '.meets'".format(nextMeet=self.upComingMeets[0]))
        self.scheduler.enter(60*60*60,50,capIzzy.updateMeetinfo,[self])

capIzzy().connect("irc.canternet.org",6667,"CaptainIzzy")
