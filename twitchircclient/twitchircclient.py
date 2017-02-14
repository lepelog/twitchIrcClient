"""
Twitch Client Library
"""

import socket
import threading
import re
import time

tags_regex='(?P<tags>([-a-zA-Z0-9_]+=[^; \n\r]*;)*([-a-zA-Z0-9_]+=[^; \n\r]*))'
username_regex='(?P<username>[a-zA-Z0-9_]+)!(?P=username)@(?P=username)'
channel_regex='#(?P<channel>[a-zA-Z0-9_]+)'

#Regex for Sent messages:
#First section are tags, some characters=something, ';'-seperated list, but there is no ; after the last one
#Followed by the username section, 'username!username@username.tmi.twitch.tv
#Followed by PRIVMSG
#Followed by #channelname
#Followed by :Message
#Groups: tags, channel, username, message
#Note: messages send by twitchnotify don't contain tags, an empty dict will be returned!
privmsg_regex = re.compile('^(@'+tags_regex+' )?:'+username_regex+r'\.tmi\.twitch\.tv PRIVMSG '+channel_regex+' :(?P<message>.*)$')

#Regex for incommig whisper-messages                                                       Notice that there is no '#' here
whisper_regex = re.compile('^@'+tags_regex+' :'+username_regex+r'\.tmi\.twitch\.tv WHISPER [a-zA-Z0-9_]+ :(?P<message>.*)$')

#Regex for user joining the channel:
join_regex = re.compile('^:'+username_regex+r'\.tmi\.twitch\.tv JOIN '+channel_regex+' *$')

#Regex for user leaving the channel:
part_regex = re.compile('^:'+username_regex+r'\.tmi\.twitch\.tv PART '+channel_regex+' *$')

#Regex for twitch notice messages:
notice_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv NOTICE '+channel_regex+' :(?P<message>.*)$')

#Regex for usernotice messages, used for resubscribers, the message is optional:
usernotice_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv USERNOTICE '+channel_regex+'( :(?P<message>.*))?$')

#Regex for roomstate_change
roomstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv ROOMSTATE '+channel_regex+'$')

#Regex for clearchat
clearchat_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv CLEARCHAT '+ channel_regex+' :(?P<username>[a-zA-Z0-9_]+)$')

#Regex for userstate
userstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv USERSTATE '+channel_regex+'$')

#Regex for globaluserstate
globaluserstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv GLOBALUSERSTATE')

#Regex for hosting
host_regex = re.compile(r'^:tmi\.twitch\.tv HOSTTARGET '+channel_regex+' :(?P<target>-|[a-zA-Z0-9_]+) (?P<viewers>[0-9]+)$')

#Regex for PONG from twitch
pong_regex = re.compile('^:tmi.twitch.tv PONG tmi.twitch.tv :(?P<message>.*)$')

def _deescape_tag(tag):
    #See IRCv3 Spec for escaping in tags
    return tag.replace('\\:',';').replace('\\s',' ').replace('\\r','\r').replace('\\n','\n').replace('\\\\','\\')

def _parse_tags(raw_tags):
    tags = {}
    for tag in raw_tags.split(';'):
        splittag = tag.split('=',1)
        tags[splittag[0]]=_deescape_tag(splittag[1])
    return tags


class EventSpreader:
    """
    Helper to spread incomming events
    Usage:
    es = EventSpreader()
    es+=handleFunc #Add a handler to the spreader
    es.spread(args) #Call all eventHandlers with the args/kwargs
    es-=handleFunc #Remove a handler from the spreader
    """
    def __init__(self):
        self.reciever=list()

    def __iadd__(self, reciever):
        self.reciever.append(reciever)

    def __isub__(self, reciever):
        self.reciever.remove(reciever)
        
    def add(self, reciever):
        self.reciever.append(reciever)

    def remove(self, reciever):
        self.reciever.remove(reciever)

    def spread(self, *args, **kwargs):
        for rec in self.reciever:
            rec(*args, **kwargs)

class TwitchIrcClient:

    def __init__(self, username, oauthtoken):
        """
        Constructor, start the connection witch create_connection
        Args:
            username (str): Your username to use for logging onto twitch
            oauthtoken (str): Your oauthtoken, retrieved from twitchTv
                See README.md for further information about oauth
        """
        self.username=username
        self.oauthtoken=oauthtoken
        self.joined_channels = set()
        self.messagespreader = EventSpreader()
        self.joinspreader = EventSpreader()
        self.partspreader = EventSpreader()
        self.noticespreader = EventSpreader()
        self.usernoticespreader = EventSpreader()
        self.roomstatespreader = EventSpreader()
        self.clearchatspreader = EventSpreader()
        self.userstatespreader = EventSpreader()
        self.globaluserstatespreader = EventSpreader()
        self.hostspreader = EventSpreader()
        self.whisperspreader = EventSpreader()

    def create_connection(self):
        """
        Create a connection to twitch, logs in with username and password and start recieving
        messages and sending them to via the EventSpreaders
        """

        #Create new Socket and connect to irc.twitch.tv
        self._connect()

        #setup for recieving messages
        def reciever():
            self.go_on=True
            self._restarting=False
            self._has_conversation=False
            while self.go_on:
                #Messages from the socket are raw bytes
                multidata = bytes()
                try:
                    #If messages are too big fetch them in multidata. The end of a message is always a newline
                    while not multidata or not multidata.endswith(b'\n'):
                        if self._restarting:
                            #during the restart of the socket, no messages can be recieved
                            continue
                        #direct decoding might fail on long non-ascii messages
                        gotdata=self._sock.recv(1024)
                        if len(gotdata)==0:
                            #Connection is lost, lets reconnect!
                            self.reconnect()
                        self._has_conversation=True
                        multidata+=gotdata
                    #Twitch can send more messages than one at once, but they are linebreak-seperated
                    decoded = multidata.decode('utf-8')
                    for data in decoded.split('\r\n'):
                        self._handle_incomming(data)
                except KeyboardInterrupt:
                    self.go_on=False
                except Exception as e:
                    if self._restarting:
                        pass #Restarting the socket causes an exception, which can be ignored
                    else:
                        print('%s error occurred:%s'%(type(e),e))
        
        def twitch_pinger():
            while self.go_on:
                time.sleep(20)
                if not self.go_on:
                    break
                if not self._has_conversation:
                    #Try pingtest 2 times, first might fail even if connection is alive
                    if not self.pingtest() or not self.pingtest():
                        self.reconnect()
                self._has_conversation=False
            
        self.irc_reciever_thread = threading.Thread(target=reciever)
        self.irc_reciever_thread.start()
        
        self.twitch_pinger_thread = threading.Thread(target=twitch_pinger)
        self.twitch_pinger_thread.start()
        
        #Set up authentication, tags, etc.
        self._begin_connection()

    def pingtest(self):
        self._gotpong=False
        tc=threading.Condition()
        with tc:
            self.send('PING me\r\n')
            return tc.wait_for(lambda: self._gotpong,20)

    def _kill_socket(self):
        """
        Shutdown the socket, it can not longer be used
        """
        self._sock.shutdown(socket.SHUT_RDWR)
        self._sock.close()

    def _connect(self):
        """
        Connect a new socket to the irc
        """
        self._sock = socket.socket()
        self._sock.connect(('irc.twitch.tv', 6667))
            
    def _begin_connection(self):
        """
        Start the conversation, requests capabilities and authenticate
        """
        self.send('CAP REQ :twitch.tv/membership\r\n')
        self.send('CAP REQ :twitch.tv/commands\r\n')
        self.send('CAP REQ :twitch.tv/tags\r\n')
        self.authenticate(self.username, self.oauthtoken)
        for channel in self.joined_channels:
            self.join(channel)
            
    def reconnect(self):
        self._restarting=True
        self._kill_socket()
        self._connect()
        self._restarting=False
        time.sleep(1)
        self._begin_connection()
        
    def shutdown(self):
        self._restarting=True
        self.go_on=False
        self._kill_socket()

    def authenticate(self, username, oauthtoken):
        """
        Authenticates at the twitchIrc with given username and oauthtoken
        Args:
            username (str): Your username to use for logging onto twitch
            oauthtoken (str): Your oauthtoken, retrieved from twitchTv
                See README.md for further information about oauth
        """
        self.send('PASS %s\r\n' % oauthtoken)
        self.send('NICK %s\r\n' % username)
        self.send('USER %s %s %s :%s\r\n' % (username, username, username, username))
        
    def send(self, msg):
        """
        Send a message directly to the twitchIrc
        Args:
            msg (str): The message to be send
        """
        self._sock.sendall(msg.encode('utf-8'))

    def sendprivmsg(self, channel, message):
        """
        Send a Message to a channel
        """
        self.send('PRIVMSG #%s :%s\r\n' % (channel.lower(), message))

    def sendwhisper(self, username, message):
        """
        Send a whisper-message to a user
        """
        self.sendprivmsg(self.username, '/w %s %s'%(username,message))

    def join(self, channel):
        """
        Join a channel to send messages to
        """
        self.joined_channels.add(channel)
        self.send('JOIN #%s\r\n'%channel)

    def part(self, channel):
        """
        Leave a channel
        """
        self.joined_channels.discard(channel)
        self.send('PART #%s\r\n'%channel)

    def timeout(self, channel, username, duration=600):
        """
        Time out a user in a channel with an optional duration in seconds (default: 600)
        You have to be moderator in the channel
        """
        self.sendprivmsg(channel, '/timeout %s %s'%(username, duration))

    def ban(self, channel, username):
        """
        Ban a user from the channel
        You have to be moderator in the channel
        """
        self.sendprivmsg(channel, '/ban %s'%username)

    def unban(self, channel, username):
        """
        Unan a user from the channel
        You have to be moderator in the channel
        """
        self.sendprivmsg(channel, '/unban %s'%username)

    def _handle_incomming(self, data):
        if not len(data):
            return
        elif data.startswith('PING'):
            #Respond to PING, looses connection otherwise
            self.send(data.replace('PING','PONG'))
        else:
            #Try to match regular expressions!
            msg_match = privmsg_regex.match(data)
            if not msg_match is None:
                self._messagerecieved(msg_match)
                return
            join_match = join_regex.match(data)
            if not join_match is None:
                self._joinrecieved(join_match)
                return
            part_match = part_regex.match(data)
            if not part_match is None:
                self._partrecieved(part_match)
                return
            notice_match = notice_regex.match(data)
            if not notice_match is None:
                self._noticerecieved(notice_match)
                return
            usernotice_match = usernotice_regex.match(data)
            if not usernotice_match is None:
                self._usernoticerecieved(usernotice_match)
                return
            roomstate_match = roomstate_regex.match(data)
            if not roomstate_match is None:
                self._roomstaterecieved(roomstate_match)
                return
            clearchat_match = clearchat_regex.match(data)
            if not clearchat_match is None:
                self._clearchatrecieved(clearchat_match)
                return
            userstate_match = userstate_regex.match(data)
            if not userstate_match is None:
                self._userstaterecieved(userstate_match)
                return
            globaluserstate_match = globaluserstate_regex.match(data)
            if not globaluserstate_match is None:
                self._globaluserstaterecieved(globaluserstate_match)
                return
            host_match = host_regex.match(data)
            if not host_match is None:
                self._hostrecieved(host_match)
                return
            whisper_match = whisper_regex.match(data)
            if not whisper_match is None:
                self._whisperrecieved(whisper_match)
                return
            pong_match = pong_regex.match(data)
            if not pong_match is None:
                self._gotpong=True
                return
            #print('"'+data+'"')

    def _messagerecieved(self, match):
        #Twtichnotify doesnt't send tags, empty dicct is returned cause it's easier to deal with
        raw_tags = match.group('tags')
        if raw_tags is None:
            tags={}
        else:
            tags=_parse_tags(raw_tags)
        username = match.group('username')
        channel = match.group('channel')
        message = match.group('message')
        self.messagespreader.spread(username=username, channel=channel, tags=tags, message=message)

    def _joinrecieved(self, match):
        username = match.group('username')
        channel = match.group('channel')
        self.joinspreader.spread(username=username,channel=channel)

    def _partrecieved(self, match):
        username = match.group('username')
        channel = match.group('channel')
        self.partspreader.spread(username=username,channel=channel)
        
    def _noticerecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        channel = match.group('channel')
        message = match.group('message')
        self.noticespreader.spread(channel=channel, message=message, tags=tags)

    def _usernoticerecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        channel = match.group('channel')
        message = match.group('message')
        #no resubcription message:
        if message is None:
            message = ''
        self.noticespreader.spread(channel=channel, message=message, tags=tags)

    def _roomstaterecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        channel = match.group('channel')
        self.roomstatespreader.spread(channel=channel, tags=tags)
        
    def _clearchatrecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        channel = match.group('channel')
        username = match.group('username')
        self.clearchatspreader.spread(channel=channel, tags=tags, username=username)
        
    def _userstaterecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        channel = match.group('channel')
        self.userstatespreader.spread(channel=channel, tags=tags)
        
    def _globaluserstaterecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        self.globaluserstatespreader.spread(tags=tags)
        
    def _hostrecieved(self, match):
        channel=match.group('channel')
        target=match.group('target')
        viewers=match.group('viewers')
        self.hostspreader.spread(channel=channel, target=target, viewers=viewers)

    def _whisperrecieved(self, match):
        tags = _parse_tags(match.group('tags'))
        username = match.group('username')
        message = match.group('message')
        self.whisperspreader.spread(username=username, message=message, tags=tags)
