#!/usr/bin/python

from ircBot import *
import urllib
import threading
from HTMLParser import HTMLParser
from datetime import datetime
import re
import sched

PASSWORD = open("pswd").read() #To avoid it ending up on github ;)
   
class meetInfo():
    def __init__(self,t,l,p,d):
        self.datetime = datetime.strptime(p,"%d %b %Y %H:%M:%S")
        self.location = d.split(" ",7)[-1] #Expermental
        self.title = t
        self.description = d
        self.link = l
        
    def __str__(self):
        return "{title}: {description} ({link})".format(title=self.title,description=self.description,link=self.link)
        
    def __eq__(self,other):
        return (
            isinstance(other,meetInfo) and
            self.link == other.link and
            self.datetime == other.datetime and
            self.title == other.title and
            self.description == other.description
        )
        
    def __ne__(self,other):
        return not self.__eq__(other)

class capIzzy(ircBot):
    def __init__(self,host,port,nick,password,autojoin=[]):
        ircBot.__init__(self,host,port,nick,password,autojoin)
        self.upComingMeets=[]
    
    def onLoggedin(self):
        self.updateMeetinfo()
        schedThread = threading.Thread(target=sched.scheduler.run,args=[self.scheduler])
        schedThread.deamon = True

    def initCommands(self):
        ircBot.initCommands(self)
        self.commands.update({
            "meets":command(0,0,self.getUpcomingMeets),
            "navigate":command(2,2,self.navigateToMeet) #Tempremenal - Not fully implmented RSS feed lacks location data
        })
        self.commands["nav"] = self.commands["navigate"]
    
    def getUpcomingMeets(self,cmdInfo):
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here are the next few upcoming meets, for help getting to them use the Navigate command: .navigate [meet no] [start location]")
        for i,m in enumerate(self.upComingMeets):
            self.send("PRIVMSG",cmdInfo["replyTo"],"[#{0}] {1}".format(i,m))
 
    def navigateToMeet(self,cmdInfo,goalMeet,startPoint):
        goalMeet = int(goalMeet)
        startPoint   = urllib.quote_plus(startPoint)
        meetLocation = urllib.quote_plus(self.upComingMeets[goalMeet].location)
        meetDate     = urllib.quote_plus(self.upComingMeets[goalMeet].datetime.strftime("%d/%m/%y"))
        meetTime     = urllib.quote_plus(self.upComingMeets[goalMeet].datetime.strftime("%H:%M"))
        self.send("PRIVMSG",cmdInfo["replyTo"],"Here you go, this should help get you here. https://maps.google.co.uk/maps?ttype=arr&dirflg=r&saddr={start}&daddr={meetLocation}&date={date}&time={time}".format(start=startPoint,meetLocation=meetLocation,date=meetDate,time=meetTime))
        
    def updateMeetinfo(self):
        curNext = None
        try:
            curNext = self.upcomingMeets[0]
        except IndexError:
            pass
        feed = urllib.urlopen("http://bristolbronies.co.uk/meet/feed/")
        data = feed.read()
        feed.close()
        match = r"<title>([^<]*)</title>\s*<link>[^<]*</link>\s*<guid>([^<]*)</guid>\s*<pubDate>([^<]*)</pubDate>\s*<description><!\[CDATA\[(.*?)]]></description>"
        self.upComingMeets = [meetInfo(t,l,p[5:-6],re.sub("<[^>]*>","",d)) for t,l,p,d in re.findall(match,data)]
        self.upComingMeets.sort(lambda a,b:(a.datetime-b.datetime).days)
        if len(self.upComingMeets) > 0 and curNext != self.upComingMeets[0]: #TODO BTAFFTP
            self.send("TOPIC","#bristolbronies","Next upcoming Bristol Bronies meet: {nextMeet}. For more upcoming meets type '.meets'".format(nextMeet=self.upComingMeets[0]))
        self.scheduler.enter(60*60,1000,capIzzy.updateMeetinfo,[self])

capIzzy("irc.canternet.org",6667,"CaptainIzzie",PASSWORD,["#bristolbronies"]).connect()

