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

    def __init__(self, username, oauthtoken, socket_timeout=40, ping_check_secs=15, debug=False):
        """
        Constructor, start the connection witch create_connection
        Args:
            username (str): Your username to use for logging onto twitch
            oauthtoken (str): Your oauthtoken, retrieved from twitchTv
                See README.md for further information about oauth
            socket_timeout (int)(seconds): set timeout for the socket in seconds (default: 40)
            ping_check_secs (int)(seonds): interval a ping is sent to twitch if there was no conversation (default: 15)
                you can turn this off by setting the value to 0
                to check if the connection is still alive
        """
        self.username=username
        self.oauthtoken=oauthtoken
        self.debug=debug
        self._socket_timeout=socket_timeout
        self.ping_check_secs=ping_check_secs
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
                        while self._restarting:
                            #during the restart of the socket, no messages can be recieved
                            continue
                        if not self.go_on:
                            break
                        #direct decoding might fail on long non-ascii messages
                        gotdata=self._sock.recv(1024)
                        if len(gotdata)==0:
                            #Connection is lost, lets reconnect!
                            self.log('reconnecting because of empty data')
                            self.reconnect()
                        self._has_conversation=True
                        multidata+=gotdata
                    #Twitch can send more messages than one at once, but they are linebreak-seperated
                    decoded = multidata.decode('utf-8')
                    for data in decoded.split('\r\n'):
                        self._handle_incomming(data)
                except KeyboardInterrupt:
                    self.go_on=False
                except socket.timeout:
                    #On timeout, restart the socket; if the chat is quiet, the twitch_pinger sends PING to twitch and forces a response
                    self.log('reconnection because of socket-timeout!')
                    self.reconnect()
                except Exception as e:
                    if self._restarting or not self.go_on:
                        self.log('Error during restart: %s'%e) #Restarting and stopping the socket causes an exception which can be ignored
                    else:
                        print('%s error occurred:%s'%(type(e),e))
        
        def twitch_pinger():
            while True:
                waiter=threading.Condition()
                with waiter:
                    #Waits for 15 seconds or stops this thread if the program is stopped
                    if waiter.wait_for(lambda: not self.go_on,self.ping_check_secs):
                        break
                    if not self._has_conversation:
                        self.log('PINGCHECK')
                        self.pingtest()
                    self._has_conversation=False
            
        self._irc_reciever_thread = threading.Thread(target=reciever)
        self._irc_reciever_thread.start()
        
        self._twitch_pinger_thread = threading.Thread(target=twitch_pinger)
        self._twitch_pinger_thread.start()
        
        #Set up authentication, tags, etc.
        self._begin_connection()

    def pingtest(self):
        """Send a ping to twitch"""
        self.send('PING twitchircclient\r\n')

    def reconnect(self):
        """reconnects to the twitchIrc"""
        self._restarting=True
        self._kill_socket()
        self._connect()
        self._restarting=False
        time.sleep(1)
        self._begin_connection()

    def shutdown(self):
        """Shutdown the irc connection"""
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
        while self._restarting:
            continue
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
        
    @property
    def socket_timeout(self):
        return self._socket_timeout

    @socket_timeout.setter
    def socket_timeout(self,to):
        if to<0:
            raise AttributeError("%s is invalid: socket_timeout can't be below 0!"%to)
        elif to==0:
            self._sock.settimeout(None)
        else:
            self._sock.settimeout(to)
        self._socket_timeout=to

    def log(self, msg):
        """logs debug messages to the console"""
        if self.debug:
            print(msg)

    #Begin "private" methods
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
        self._sock.settimeout(self.socket_timeout)

    def _begin_connection(self):
        """
        Start the conversation, requests capabilities, authenticates and joins previously joined channels
        """
        self.send('CAP REQ :twitch.tv/membership\r\n')
        self.send('CAP REQ :twitch.tv/commands\r\n')
        self.send('CAP REQ :twitch.tv/tags\r\n')
        self.authenticate(self.username, self.oauthtoken)
        for channel in self.joined_channels:
            self.join(channel)

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
            self.log('"'+data+'"')

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
        self.usernoticespreader.spread(channel=channel, message=message, tags=tags)

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
