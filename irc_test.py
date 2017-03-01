#!/bin/python3
from twitchircclient import TwitchIrcClient
import time
from test_config import *

def messagelistener(channel, username, tags, message):
    print('\nuser:%s\nchannel:%s\ntags:%s\nmessage:"%s"'%(username,channel,tags,message))

def whisperlistener(username, tags, message):
    print('\n%s WHISPERED:\nmessage:"%s"\ntags:%s'%(username,message,tags))

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
    
def hostlistener(channel, target, viewers):
    print('!HOST\n%s hosts %s with %s viewer(s)'%(channel, target,viewers))

def gainoperatorlistener(channel, username):
    print('<%s gained operator in %s>'%(username, channel))

def looseoperatorlistener(channel, username):
    print('<%s lost operator in %s>'%(username, channel))

if __name__=='__main__':
    irc = TwitchIrcClient(username,oauth_token,debug=debug)
    irc.messagespreader.add(messagelistener)
    irc.whisperspreader.add(whisperlistener)
    irc.joinspreader.add(joinlistener)
    irc.partspreader.add(partlistener)
    irc.roomstatespreader.add(roomstatelistener)
    irc.noticespreader.add(noticelistener)
    irc.clearchatspreader.add(clearchatlistener)
    irc.userstatespreader.add(userstatelistener)
    irc.globaluserstatespreader.add(globaluserstatelistener)
    irc.hostspreader.add(hostlistener)
    irc.gainoperatorspreader.add(gainoperatorlistener)
    irc.looseoperatorspreader.add(looseoperatorlistener)
    irc.create_connection()
    irc.join(channel)
