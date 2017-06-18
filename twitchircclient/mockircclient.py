from .twitchircclient import *

class MockIrcClient(TwitchIrcClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        def _rec(msg):
            pass
        self.send_reciever=_rec

    def create_connection(self):
        pass
    
    def reconnect(self):
        pass
        
    def shutdown(self):
        pass

    def send(self, msg):
        self.log(msg)
        self.send_reciever(msg)

    def mock_msg_incomming(self, msg):
        self.log(msg)
        self._handle_incomming(msg)

    def set_send_reciever(self, reciever):
        self.send_reciever=reciever

    @staticmethod
    def generate_mock_privmsg(channel, username, message, tags={}):
        #There need to be at least one tag
        tags.update({'a':'b'})
        tagstring=';'.join(tagn+'='+tagv for tagn, tagv in tags.items())
        return '@{tagstring} :{username}!{username}@{username}.tmi.twitch.tv PRIVMSG #{channel} :{message}'.format(tagstring=tagstring, username=username, message=message, channel=channel)
    
    @staticmethod
    def generate_mock_whisper(username, message, tags={}):
        #There need to be at least one tag
        tags.update({'a':'b'})
        tagstring=';'.join(tagn+'='+tagv for tagn, tagv in tags.items())
        return '@{tagstring} :{username}!{username}@{username}.tmi.twitch.tv WHISPER {username} :{message}'.format(tagstring=tagstring, username=username, message=message)

    
    def _kill_socket(self):
        pass
        
    def _connect(self):
        pass
