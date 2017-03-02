# Simple TwitchIRC-Client
Fully written in Python3

##Installation
###From github
Run `pip3 install https://github.com/lepelog/twitchIrcClient/archive/master.zip`

###From source
Clone the Repository, change to this directory and execute `python3 setup.py install`.

###Local installation
If you don't have root-privileges and/or want to install the package just for yourself, use the `--user`-Flag at the end of the command.

###Uninstall
To uninstall this package with pip run `pip3 uninstall twitchircclient`

##Features
- Joining/Parting multiple channels
- Reading/Sending messages
- Catching Events such as people joining/parting, roomstate changes, twitch notices etc.
- Sending/Recieving Whisper-messages

##Usage
Import the TwitchIrcClient from twitchircclient and start the connection. Example:
```python
from twitchircclient import TwitchIrcClient

#Instantiate the client with username and oauth-token
irc = TwitchIrcClient('username','oauth:p4ssw0rd')

#Define a message-reciever-function.
#Signatures for each listener are described below
def messagelistener(username, channel, tags, message):
    print('message: '+message)

#Register the listener for recieving messages
irc.messagespreader.add(messagelistener)

#Create the connecion to the twitchIrc, logging in
#Now it starts recieving messages etc.
irc.create_connection()

#Joins the channel 'channel'
#you only recieve messages sent in a channel if you are logged in
irc.join('channel')

#Send a message to a channel
irc.sendprivmsg('channel','Kappa')

#Stop the listener from recieving messages
irc.messagespreader.remove(messagelistener)

#Send a whisper a user
irc.sendwhisper('username','OpieOP')
```

### Notes about oauth-token
Use the [Twitch-Oauth-Generator](https://twitchapps.com/tmi/) to create your oauth-token which is needed to connect to twitchIrc. **Copy the whole token**, with the `oauth:`-prefix.

### Notes about `irc_test.py`
To test the basic functionality of this library there is `irc_test.py`, but it needs a username, a oauth-token and a channel to join, which should **not** be public. This information is stored in `test-config.py`, which is not commited. If you want to run the test, copy `test-config-example.py`, rename the copy to `test-config.py` and replace the placeholders with your config.

## Reciever-functions
To recieve one of these events, write a function with the specific signature and add it to the specific `EventSpreader`, Attributes of the TwitchIrcClient-instance. Add a listener with add, as described in the example above.  
Name of the `EventSpreader`s and their signature:

**messagespreader**: Used if a user sends a message in a channel you are joined in:  
`channel, username, tags, message`

**whisperspreader**: Used if a user whispers a message directly to you:  
`username, tags, message`

**joinspreader**: Used if a user joins a channel you are joined in:  
`channel, username`

**partspreader**: Used if a user parts a channel you are joined in:  
`channel, username`

**roomstatespreader**: Used if you join a channel or if the roomstate changes in a channel you are joined in:  
`channel, tags`

**usernoticespreader**: Used if  a user resubscribes:  
`channel, tags, message`

**noticespreader**: Used if twitch sends a notification:  
`channel, tags, message`

**clearchatspreader**: Used if someone got timeuted or banned:  
`channel, tags, username`

**globaluserstatespreader**: Used if you create the connection, informs about your global config:  
`tags`

**userstatespreader**: Used if you join a channel, informs about your state in the channel:    
`channel, tags`

**hostspreader**: Used if the joined channel starts/stops hosting another channel:  
`channel`, `target`, `viewers`

**gainoperatorspreader**: Used if a mod joins a channel:  
`channel, username`

**looseoperatorspreader**: Used if a mod leaves a channel:  
`channel, username`

See [Twtich IRC documentation](https://github.com/justintv/Twitch-API/blob/master/IRC.md) for more information.