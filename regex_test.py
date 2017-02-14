#!/bin/python3

import unittest
from twitchircclient import TwitchIrcClient

class ExpectedException(Exception):
    
    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message=message
        

class MockIrcClient(TwitchIrcClient):
    
    def __init__(self):
        super().__init__('','')
    
    def send(self, msg):
        raise ExpectedException(msg)
        
def listenerbuilder(testcase,**expected_args):
    def listener(**kwargs):
        testcase.assertEqual(expected_args, kwargs)
    return listener

class RegexTest(unittest.TestCase):

    def setUp(self):
        #Instanitate mocked Client, but dont start
        self.irc = MockIrcClient()
        
    #test all cases from https://github.com/justintv/Twitch-API/blob/master/IRC.md
    def testPRIVMSG1(self):
        tags={'badges':'global_mod/1,turbo/1','color':'#0D4200','display-name':'TWITCH_UserNaME','emotes':'25:0-4,12-16/1902:6-10','mod':'0','room-id':'1337','subscriber':'0','turbo':'1','user-id':'1337','user-type':'global_mod'}
        
        msglistener=listenerbuilder(self, channel='channel', username='twitch_username',message='Kappa Keepo Kappa', tags=tags)
        self.irc.messagespreader.add(msglistener)
        msg = '@badges=global_mod/1,turbo/1;color=#0D4200;display-name=TWITCH_UserNaME;emotes=25:0-4,12-16/1902:6-10;mod=0;room-id=1337;subscriber=0;turbo=1;user-id=1337;user-type=global_mod :twitch_username!twitch_username@twitch_username.tmi.twitch.tv PRIVMSG #channel :Kappa Keepo Kappa'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.messagespreader.remove(msglistener)
    
    def testPRIVMSG2(self):
        tags={'badges':'staff/1,bits/1000','bits':'100','color':'','display-name':'TWITCH_UserNaME','emotes':'','id':'b34ccfc7-4977-403a-8a94-33c6bac34fb8','mod':'0','room-id':'1337','subscriber':'0','turbo':'1','user-id':'1337','user-type':'staff'}
        
        msglistener=listenerbuilder(self, channel='channel', username='twitch_username',message='cheer100', tags=tags)
        self.irc.messagespreader.add(msglistener)
        msg = '@badges=staff/1,bits/1000;bits=100;color=;display-name=TWITCH_UserNaME;emotes=;id=b34ccfc7-4977-403a-8a94-33c6bac34fb8;mod=0;room-id=1337;subscriber=0;turbo=1;user-id=1337;user-type=staff :twitch_username!twitch_username@twitch_username.tmi.twitch.tv PRIVMSG #channel :cheer100'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.messagespreader.remove(msglistener)
            
    #Example with twitchnotify without tags
    def testPRIVMSG3(self):
        msglistener=listenerbuilder(self, channel='channel', username='twitchnotify',message='username subscribe with twitch-prime!', tags={})
        self.irc.messagespreader.add(msglistener)
        msg = ':twitchnotify!twitchnotify@twitchnotify.tmi.twitch.tv PRIVMSG #channel :username subscribe with twitch-prime!'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.messagespreader.remove(msglistener)
            
    def testUSERSTATE(self):
        tags={'color':'#0D4200','display-name':'TWITCH_UserNaME','emote-sets':'0,33,50,237,793,2126,3517,4578,5569,9400,10337,12239','mod':'1','subscriber':'1','turbo':'1','user-type':'staff'}
        
        userlistener=listenerbuilder(self, channel='channel', tags=tags)
        self.irc.userstatespreader.add(userlistener)
        msg='@color=#0D4200;display-name=TWITCH_UserNaME;emote-sets=0,33,50,237,793,2126,3517,4578,5569,9400,10337,12239;mod=1;subscriber=1;turbo=1;user-type=staff :tmi.twitch.tv USERSTATE #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.userstatespreader.remove(userlistener)
            
    def testGLOBALUSERSTATE(self):
        tags={'color':'#0D4200','display-name':'TWITCH_UserNaME','emote-sets':'0,33,50,237,793,2126,3517,4578,5569,9400,10337,12239','turbo':'0','user-id':'1337','user-type':'admin'}
        
        globallistener=listenerbuilder(self,tags=tags)
        self.irc.globaluserstatespreader.add(globallistener)
        msg='@color=#0D4200;display-name=TWITCH_UserNaME;emote-sets=0,33,50,237,793,2126,3517,4578,5569,9400,10337,12239;turbo=0;user-id=1337;user-type=admin :tmi.twitch.tv GLOBALUSERSTATE'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.globaluserstatespreader.add(globallistener)
            
    def testROOMSTATE1(self):
        tags={'broadcaster-lang':'','r9k':'0','slow':'0','subs-only':'0'}
        roomstatelistener=listenerbuilder(self, channel='channel', tags=tags)
        self.irc.roomstatespreader.add(roomstatelistener)
        msg='@broadcaster-lang=;r9k=0;slow=0;subs-only=0 :tmi.twitch.tv ROOMSTATE #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.roomstatespreader.remove(roomstatelistener)
            
    def testROOMSTATE2(self):
        roomstatelistener=listenerbuilder(self, channel='channel', tags={'slow':'10'})
        self.irc.roomstatespreader.add(roomstatelistener)
        msg='@slow=10 :tmi.twitch.tv ROOMSTATE #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.roomstatespreader.remove(roomstatelistener)
            
    def testUSERNOTICE1(self):
        tags={'badges':'staff/1,broadcaster/1,turbo/1','color':'#008000','display-name':'TWITCH_UserName','emotes':'','mod':'0','msg-id':'resub','msg-param-months':'6','room-id':'1337','subscriber':'1','system-msg':'TWITCH_UserName has subscribed for 6 months!','login':'twitch_username','turbo':'1','user-id':'1337','user-type':'staff'}
        usernoticelistener=listenerbuilder(self,channel='channel', message='Great stream -- keep it up!', tags=tags)
        self.irc.usernoticespreader.add(usernoticelistener)
        msg='@badges=staff/1,broadcaster/1,turbo/1;color=#008000;display-name=TWITCH_UserName;emotes=;mod=0;msg-id=resub;msg-param-months=6;room-id=1337;subscriber=1;system-msg=TWITCH_UserName\shas\ssubscribed\sfor\s6\smonths!;login=twitch_username;turbo=1;user-id=1337;user-type=staff :tmi.twitch.tv USERNOTICE #channel :Great stream -- keep it up!'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.usernoticespreader.remove(usernoticelistener)
            
    def testUSERNOTICE2(self):
        tags={'badges':'staff/1,broadcaster/1,turbo/1','color':'#008000','display-name':'TWITCH_UserName','emotes':'','mod':'0','msg-id':'resub','msg-param-months':'6','room-id':'1337','subscriber':'1','system-msg':'TWITCH_UserName has subscribed for 6 months!','login':'twitch_username','turbo':'1','user-id':'1337','user-type':'staff'}
        usernoticelistener=listenerbuilder(self,channel='channel', message='', tags=tags)
        self.irc.usernoticespreader.add(usernoticelistener)
        msg='@badges=staff/1,broadcaster/1,turbo/1;color=#008000;display-name=TWITCH_UserName;emotes=;mod=0;msg-id=resub;msg-param-months=6;room-id=1337;subscriber=1;system-msg=TWITCH_UserName\shas\ssubscribed\sfor\s6\smonths!;login=twitch_username;turbo=1;user-id=1337;user-type=staff :tmi.twitch.tv USERNOTICE #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.usernoticespreader.remove(usernoticelistener)
            
    def testCLEARCHAT1(self):
        tags={'ban-duration':'1','ban-reason':'Follow the rules'}
        clearchatlistener=listenerbuilder(self, channel ='channel',username='target_username',tags=tags)
        self.irc.clearchatspreader.add(clearchatlistener)
        msg='@ban-duration=1;ban-reason=Follow\sthe\srules :tmi.twitch.tv CLEARCHAT #channel :target_username'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.clearchatspreader.remove(clearchatlistener)
            
    def testCLEARCHAT2(self):
        tags={'ban-reason':'Follow the rules'}
        clearchatlistener=listenerbuilder(self, channel ='channel',username='target_username',tags=tags)
        self.irc.clearchatspreader.add(clearchatlistener)
        msg='@ban-reason=Follow\sthe\srules :tmi.twitch.tv CLEARCHAT #channel :target_username'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.clearchatspreader.remove(clearchatlistener)
            
    def testJOIN(self):
        joinlistener=listenerbuilder(self, channel='channel', username='twitch_username')
        self.irc.joinspreader.add(joinlistener)
        msg=':twitch_username!twitch_username@twitch_username.tmi.twitch.tv JOIN #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.joinspreader.remove(joinlistener)
            
    def testPART(self):
        partlistener=listenerbuilder(self, channel='channel', username='twitch_username')
        self.irc.partspreader.add(partlistener)
        msg=':twitch_username!twitch_username@twitch_username.tmi.twitch.tv JOIN #channel'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.partspreader.remove(partlistener)
            
    def testNOTICE(self):
        tags={'msg-id':'slow_off'}
        noticelistener=listenerbuilder(self, channel='channel', tags=tags, message='This room is no longer in slow mode.')
        self.irc.noticespreader.add(noticelistener)
        msg='@msg-id=slow_off :tmi.twitch.tv NOTICE #channel :This room is no longer in slow mode.'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.noticespreader.remove(noticelistener)
            
    def testPING(self):
        msg='PING tmi.twitch.tv'
        try:
            self.irc._handle_incomming(msg)
        except ExpectedException as e:
            self.assertEqual(e.message,'PONG tmi.twitch.tv')
            
    def testHOST1(self):
        hostlistener=listenerbuilder(self, channel='hosting_channel', target='target_channel', viewers='42')
        self.irc.hostspreader.add(hostlistener)
        msg=':tmi.twitch.tv HOSTTARGET #hosting_channel :target_channel 42'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.hostspreader.remove(hostlistener)
            
    def testHOST2(self):
        hostlistener=listenerbuilder(self, channel='hosting_channel', target='-', viewers='42')
        self.irc.hostspreader.add(hostlistener)
        msg=':tmi.twitch.tv HOSTTARGET #hosting_channel :- 42'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.hostspreader.remove(hostlistener)

    def testWHISPER(self):
        tags={'badges':'','color':'#FF0000','display-name':'UserName','emotes':'','message-id':'3','thread-id':'123456789_123456789','turbo':'0','user-id':'123456789','user-type':''}
        whisperlistener=listenerbuilder(self, username='username', message='hi', tags=tags)
        self.irc.whisperspreader.add(whisperlistener)
        msg='@badges=;color=#FF0000;display-name=UserName;emotes=;message-id=3;thread-id=123456789_123456789;turbo=0;user-id=123456789;user-type= :username!username@username.tmi.twitch.tv WHISPER channel :hi'
        try:
            self.irc._handle_incomming(msg)
        finally:
            self.irc.whisperspreader.remove(whisperlistener)
