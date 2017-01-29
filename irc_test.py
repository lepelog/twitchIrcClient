#!/bin/python3
from twitchIrcClient import TwitchIrcClient
import time
from test_config import *

def messagelistener(channel, username, tags, message):
    print('\nuser:%s\nchannel:%s\ntags:%s\nmessage:"%s"'%(username,channel,tags,message))

def joinlistener(channel, username):
    print('<%s joined %s>'%(username, channel))

def partlistener(channel, username):
    print('<%s left %s>'%(username, channel))

def roomstatelistener(channel, tags):
    print('!ROOMSTATE IN #%s\n%s'%(channel,tags))

def noticelistener(channel, tags, message):
    print('!NOTICE #%s\n%s\n%s'%(channel,tags,message))
    
def clearchatlistener(channel, tags, username):
    print('!CLEARCHAT from %s in %s\n%s'%(username,channel,tags))

def globaluserstatelistener(tags):
    print('!GLOBALUSERSTATE: %s'%tags)

def userstatelistener(channel, tags):
    print('!USERSTATE in %s:\n%s'%(channel,tags))

if __name__=='__main__':
    irc = TwitchIrcClient(username,oauth_token)            
    irc.messagespreader.add(messagelistener)
    irc.joinspreader.add(joinlistener)
    irc.partspreader.add(partlistener)
    irc.roomstatespreader.add(roomstatelistener)
    irc.noticespreader.add(noticelistener)
    irc.clearchatspreader.add(clearchatlistener)
    irc.userstatespreader.add(userstatelistener)
    irc.globaluserstatespreader.add(globaluserstatelistener)
    irc.create_connection()
    irc.join(channel)
