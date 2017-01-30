# Simple TwitchIRC-Client
Fully written in Python3

##Features
- Joining/Parting multiple channels
- Reading/Sending messages
- Catching Events such as people joining/parting, roomstate changes, twitch notices etc.

##Usage
Import the twitchIrcClientLib, instatiate a TwichIrcConnection and start the connection. Example:
```python
from TwitchIrcClient import twitchIrcClient as twitchirc

#Instantiate the client with username and oauth-token
irc = twitchirc.TwitchIrcClient('username','oauth:p4ssw0rd')

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

**joinspreader**: Used if a user joins a channel you are joined in:  
`channel, username`

**partspreader**: Used if a user parts a channel you are joined in:  
`channel, username`

**roomstatespreader**: Used if you join a channel or if the roomstate changes in a channel you are joined in:  
`channel, tags`

**noticespreader**: Used if twitch sends a notification:  
`channel, tags, message`

**clearchatspreader**: Used if someone got timeuted or banned:  
`channel, tags, username`

**globaluserstatespreader**: Used if you create the connection, informs about your global config:  
`tags`

**userstatespreader**: Used if you join a channel, informs about your state in the channel:    
`channel, tags`

See [Twtich IRC documentation](https://github.com/justintv/Twitch-API/blob/master/IRC.md#tags) for more information.