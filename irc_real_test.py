#!/bin/python3
from twitchircclient import TwitchIrcClient
import time
from test_config import *

#This is a python-script for testing the client automatically
#It joins the given usernames own channel (to have mod privelegies) and test sending messages,
#getting notes, timeouts, changing roomstate and so on.

#TODO: Add test of part and privmsg

if __name__=='__main__':
    #Instantiate irc
    irc = TwitchIrcClient(username, oauth_token)
    orig_username=username
    #Setup for getting roomstatenotice
    roomstate = {}
    def roomstatelistener(channel, tags):
        global roomstate
        assert channel == username
        roomstate=tags
        
    irc.roomstatespreader.add(roomstatelistener)
    
    #Setup to catch our join
    selfjoin = False
    def joinlistener(channel, username):
        global selfjoin
        assert channel == orig_username
        selfjoin = (orig_username==username)
    irc.joinspreader.add(joinlistener)
    
    #Setup to check if there was a global userstate notice
    gotglobaluserstate = False
    def globaluserstatelistener(tags):
        global gotglobaluserstate
        gotglobaluserstate=True
        
    irc.globaluserstatespreader.add(globaluserstatelistener)
    
    #Setup to get channel userstate
    userstate = {}
    def userstatelistener(channel, tags):
        global userstate
        assert channel == username
        userstate=tags
    irc.userstatespreader.add(userstatelistener)
    
    #Setup to get notices
    notice = None
    def noticelistener(channel, tags, message):
        global notice
        assert channel == username
        notice=(tags,message)
    irc.noticespreader.add(noticelistener)
    
    #Setup to catch timeout
    timeout = None
    def clearchatlistener(channel, username,tags):
        global timeout
        assert channel == orig_username
        timeout=(tags, username)
    irc.clearchatspreader.add(clearchatlistener)
    irc.create_connection()
    irc.join(username)
    time.sleep(2)
    assert gotglobaluserstate
    assert selfjoin
    assert not userstate == {}
    assert 'broadcaster/1' in userstate['badges']
    assert not roomstate == {}
    
    #Change Roomstate:
    irc.sendprivmsg(username, '/slow 123')
    time.sleep(2)
    #Roomstate changed:
    assert roomstate == {'slow':'123'}
    #Got notice:
    assert notice[0]['msg-id'] == 'slow_on'
    assert notice[1] == 'This room is now in slow mode. You may send messages every 123 seconds.'
    irc.sendprivmsg(username, '/slowoff')
    
    #Timeout somebody to recieve a 'clearchat'-command
    totimeout = 'lepelog'#Time me out, its ok. The username has to exist, unfortunally
    irc.sendprivmsg(username, '/timeout '+totimeout+' 1')
    time.sleep(2)
    assert timeout[0]['ban-duration'] == '1'
    assert timeout[1] == totimeout
    print('all tests successfull!')
    irc.shutdown()
