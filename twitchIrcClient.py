"""
Twitch Client Library
"""

import socket
import threading
import re

tags_regex='(?P<tags>([-a-zA-Z0-9_]+=[^; \\\\\n\r]*;)*([-a-zA-Z0-9_]+=[^; \\\\\n\r]*))'
username_regex='(?P<username>[a-zA-Z0-9_]+)!(?P=username)@(?P=username)'
channel_regex='#(?P<channel>[a-zA-Z0-9_]+)'

#Regex for Sent messages:
#First section are tags, some characters=something, ';'-seperated list, but there is no ; after the last one
#Followed by the username section, 'username!username@username.tmi.twitch.tv
#Followed by PRIVMSG
#Followed by #channelname
#Followed by :Message
#Groups: tags, channel, username, message
privmsg_regex = re.compile('^@'+tags_regex+' :'+username_regex+r'\.tmi\.twitch\.tv PRIVMSG '+channel_regex+' :(?P<message>.*)$')

#Regex for user joining the channel:
join_regex = re.compile('^:'+username_regex+r'\.tmi\.twitch\.tv JOIN '+channel_regex+' *$')

#Regex for user leaving the channel:
part_regex = re.compile('^:'+username_regex+r'\.tmi\.twitch\.tv PART '+channel_regex+' *$')

#Regex for twitch notice messages:
notice_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv NOTICE '+channel_regex+' :(?P<message>.*)$')

#Regex for roomstate_change
roomstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv ROOMSTATE '+channel_regex+'$')

#Regex for clearchat
clearchat_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv CLEARCHAT '+ channel_regex+' :(?P<username>[a-zA-Z0-9_]+)$')

#Regex for userstate
userstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv USERSTATE '+channel_regex+'$')

#Regex for globaluserstate
globaluserstate_regex = re.compile('^@'+tags_regex+r' :tmi\.twitch\.tv GLOBALUSERSTATE')

def _deescape_tag(tag):
    #See IRCv3 Spec for escaping in tags
    return tag.replace('\\:',';').replace('\\s',' ').replace('\\r','\r').replace('\\n','\n').replace('\\\\','\\')

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
        self.roomstatespreader = EventSpreader()
        self.clearchatspreader = EventSpreader()
        self.userstatespreader = EventSpreader()
        self.globaluserstatespreader = EventSpreader()

    def create_connection(self):
        """
        Create a connection to twitch, logs in with username and password and start recieving
        messages and sending them to via the EventSpreaders
        """

        #Create new Socket and connect to irc.twitch.tv
        self._sock = socket.socket()
        self.connect(kill_old=False)

        #Authentication
        self.authenticate(self.username, self.oauthtoken)

        #setup for recieving messages
        def reciever():
            self.go_on=True
            while self.go_on:
                multidata = ''
                try:
                    #If messages are too big fetch them in multidata
                    while not multidata or not multidata[-1]=='\n':
                        gotdata=self._sock.recv(1024).decode('utf-8')
                        if len(gotdata)==0:
                            #Connection is lost, lets reconnect!
                            self.connect()
                        multidata+=gotdata
                    #Twitch can send more messages than one at once, but the are linebreak-seperated
                    for data in multidata.split('\r\n'):
                        if not len(data):
                            continue
                        elif data.startswith('PING'):
                            #Respond to PING, looses connection otherwise
                            self.send(data.replace('PING','PONG'))
                        else:
                            #Try to match regular expressions!
                            msg_match = privmsg_regex.match(data)
                            if not msg_match is None:
                                self._messagerecieved(msg_match)
                                continue
                            join_match = join_regex.match(data)
                            if not join_match is None:
                                self._joinrecieved(join_match)
                                continue
                            part_match = part_regex.match(data)
                            if not part_match is None:
                                self._partrecieved(part_match)
                                continue
                            notice_match = notice_regex.match(data)
                            if not notice_match is None:
                                self._noticerecieved(notice_match)
                                continue
                            roomstate_match = roomstate_regex.match(data)
                            if not roomstate_match is None:
                                self._roomstaterecieved(roomstate_match)
                                continue
                            clearchat_match = clearchat_regex.match(data)
                            if not clearchat_match is None:
                                print('ccmatch')
                                self._clearchatrecieved(clearchat_match)
                                continue
                            userstate_match = userstate_regex.match(data)
                            if not userstate_match is None:
                                print('ccmatch')
                                self._userstaterecieved(userstate_match)
                                continue
                            globaluserstate_match = globaluserstate_regex.match(data)
                            if not globaluserstate_match is None:
                                print('ccmatch')
                                self._globaluserstaterecieved(globaluserstate_match)
                                continue
                            print('"'+data+'"')
                except KeyboardInterrupt:
                    self.go_on=False
                except Exception as e:
                    print('%serror occurred:%s'%(type(e),e))
        self.irc_reciever_thread = threading.Thread(target=reciever)
        self.irc_reciever_thread.start()

    def connect(self, kill_old=True):
        """
        Connects to the twitchIrc, authenticates and joines joined channels
        Args:
            kill_old (bool): If true (standard) kills the old socket, False is only for the start
        """
        if kill_old:
            self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
        self._sock = socket.socket()
        self._sock.connect(('irc.twitch.tv', 6667))
        self.send('CAP REQ :twitch.tv/membership\r\n')
        self.send('CAP REQ :twitch.tv/commands\r\n')
        self.send('CAP REQ :twitch.tv/tags\r\n')
        self.authenticate(self.username, self.oauthtoken)
        for channel in self.joined_channels:
            self.join(channel)

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

    def _messagerecieved(self, match):
        raw_tags = match.group('tags')
        username = match.group('username')
        channel = match.group('channel')
        message = match.group('message')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
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
        raw_tags = match.group('tags')
        channel = match.group('channel')
        message = match.group('message')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
        self.noticespreader.spread(channel=channel, message=message, tags=tags)

    def _roomstaterecieved(self, match):
        raw_tags = match.group('tags')
        channel = match.group('channel')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
        self.roomstatespreader.spread(channel=channel, tags=tags)
        
    def _clearchatrecieved(self, match):
        raw_tags = match.group('tags')
        channel = match.group('channel')
        username = match.group('username')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
        self.clearchatspreader.spread(channel=channel, tags=tags, username=username)
        
    def _userstaterecieved(self, match):
        raw_tags = match.group('tags')
        channel = match.group('channel')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
        self.userstatespreader.spread(channel=channel, tags=tags)
        
    def _globaluserstaterecieved(self, match):
        raw_tags = match.group('tags')
        tags = {}
        for tag in raw_tags.split(';'):
            splittag = tag.split('=',1)
            tags[splittag[0]]=_deescape_tag(splittag[1])
        self.globaluserstatespreader.spread(tags=tags)