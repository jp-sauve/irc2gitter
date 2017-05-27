import sys

from twisted.internet import defer, endpoints, protocol, reactor, task
from twisted.python import log
from twisted.words.protocols import irc


class MyFirstIRCProtocol(irc.IRCClient):
    nickname = 'Gunicorn'

    def __init__(self):
        self.deferred = defer.Deferred()

    def connectionLost(self, reason):
        self.deferred.errback(reason)

    def signedOn(self):
        # This is called once the server has acknowledged that we sent
        # both NICK and USER.
        for channel in self.factory.channels:
            self.join(channel)

    def userJoined(self, user, channel):
        nick, sep, host = user.partition('!')
        mesg = '%s: %s' % ('Nick', user)
        self._sendMessage(channel, mesg)
        mesg = '%s: %s' % ('Sep', sep)
        self._sendMessage(channel, mesg)
        mesg = '%s: %s' % ('Host', host)
        self._sendMessage(channel, mesg)
        self._sendMessage(channel, "heya brah")
    # Obviously, called when a PRIVMSG is received.

    def privmsg(self, user, channel, message):
        nick, _, host = user.partition('!')
        message = message.strip()
        if not message.startswith('!'):  # not a trigger command
            self._sendMessage(channel,"No commands? Weakling!")
            return  # so do nothing
        command, sep, rest = message.lstrip('!').partition(' ')
        # Get the function corresponding to the command given.
        func = getattr(self, 'command_' + command, None)
        # Or, if there was no function, ignore the message.
        if func is None:
            return
        # maybeDeferred will always return a Deferred. It calls func(rest), and
        # if that returned a Deferred, return that. Otherwise, return the
        # return value of the function wrapped in
        # twisted.internet.defer.succeed. If an exception was raised, wrap the
        # traceback in twisted.internet.defer.fail and return that.
        d = defer.maybeDeferred(func, rest)
        # Add callbacks to deal with whatever the command results are.
        # If the command gives error, the _show_error callback will turn the
        # error into a terse message first:
        d.addErrback(self._showError)
        # Whatever is returned is sent back as a reply:
        if channel == self.nickname:
            # When channel == self.nickname, the message was sent to the bot
            # directly and not to a channel. So we will answer directly too:
            d.addCallback(self._sendMessage, nick)
        else:
            # Otherwise, send the answer to the channel, and use the nick
            # as addressing in the message itself:
            d.addCallback(self._sendMessage, channel, nick)

    def _sendMessage(self, msg, target, nick=None):
        if nick:
            msg = '%s, %s' % (nick, msg)
        self.msg(target, msg)

    def _showError(self, failure):
        return failure.getErrorMessage()

    def command_ping(self, rest):
        return 'Pong!'

    def command_popwindow(self, rest):
        d = defer.Deferred()
        rest = rest.strip()
        wsize, hsize, botwindowtitle = rest.split(' ')
        botwindow = QtGui.QApplication(sys.argv)
        w = QtGui.QWidget()
        w.resize(int(wsize),int(hsize))
        w.move(300,300)
        w.setWindowTitle(str(botwindowtitle))
        w.show()
        sys.exit(botwindow.exec_())

    def command_saylater(self, rest):
        when, sep, msg = rest.partition(' ')
        when = int(when)
        d = defer.Deferred()
        # A small example of how to defer the reply from a command. callLater
        # will callback the Deferred with the reply after so many seconds.
        reactor.callLater(when, d.callback, msg)
        # Returning the Deferred here means that it'll be returned from
        # maybeDeferred in privmsg.
        return d


class MyFirstIRCFactory(protocol.ReconnectingClientFactory):
    protocol = MyFirstIRCProtocol
    channels = ['##Gunicorn-Special']


def main(reactor, description):
    endpoint = endpoints.clientFromString(reactor, description)
    factory = MyFirstIRCFactory()
    d = endpoint.connect(factory)
    d.addCallback(lambda protocol: protocol.deferred)
    return d

if __name__ == '__main__':
    log.startLogging(sys.stderr)

task.react(main, ['tcp:irc.freenode.net:6667'])
