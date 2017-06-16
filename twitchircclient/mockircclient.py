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
    
    def _kill_socket(self):
        pass
        
    def _connect(self):
        pass
