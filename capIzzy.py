#!/usr/bin/python

from ircBot import *
import urllib
from HTMLParser import HTMLParser
from datetime import datetime
import re

PASSWORD = open("pswd").read() #To avoid it ending up on github ;)
   
class meetInfo():
    def __init__(self,t,l,p,d):
        self.datetime = datetime.strptime(p,"%d %b %Y %H:%M:%S")
        #self.location = None #Lacking data
        self.title = t
        self.description = d
        self.link = l
        
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
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here are the next few upcoming meets")#TODO navigation#, for help getting to them use the Navigate command: .navigate [start location] [meet no]")
        for i,m in enumerate(self.upComingMeets):
            self.send("PRIVMSG",cmdInfo["replyTo"],"[#{0}] {1}".format(i,m))
 
    def navigateToMeet(self,cmdInfo,startPoint,goalMeet):
        meetLocation = urllib.quote_plus(upcomingMeets[goalMeet].location)
        meetDate = urllib.quote_plus(upcomingMeets[goalMeet].datetime.strftime("%d/%m/%y"))
        meetTime = urllib.quote_plus(upcomingMeets[goalMeet].datetime.strftime("%H:%M"))
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here you go, this should help get you here. https://maps.google.co.uk/maps?ttype=arr&dirflg=r&saddr={start}&daddr={meetLocation}&date={date}&time={time}".format(start=startPoint,meetLocation=meetLocation,date=meetDate,time=meetTime))
        
    def updateMeetinfo(self): #TODO multithread?
        feed = urllib.urlopen("http://bristolbronies.co.uk/meet/feed/")
        data = feed.read()
        feed.close()
        match = r"<title>([^<]*)</title>\s*<link>[^<]*</link>\s*<guid>([^<]*)</guid>\s*<pubDate>([^<]*)</pubDate>\s*<description><!\[CDATA\[(.*?)]]></description>"
        self.upComingMeets = [meetInfo(t,l,p[5:-6],re.sub("<[^>]*>","",d)) for t,l,p,d in re.findall(match,data)]
        self.upComingMeets.sort(lambda a,b:(a.datetime-b.datetime).days)
        if len(self.upComingMeets) > 1:
            self.send("TOPIC","#bristolbronies","Next upcoming Bristol Bronies meet: {nextMeet}. For more upcoming meets type '.meets'".format(nextMeet=self.upComingMeets[0]))
        self.scheduler.enter(60,50,capIzzy.updateMeetinfo,[self])

capIzzy().connect("irc.canternet.org",6667,"CaptainIzzy")
