# based on https://gist.github.com/jexhson/3496039

import imaplib2, time, email, urllib, json, sys
from threading import *

import config

APPNAME = "Ubuntu notifications IMAP daemon"

# This is the threading object that does all the waiting on 
# the event
class Idler(object):
    def __init__(self, conn, caxton_token):
        self.thread = Thread(target=self.idle)
        self.M = conn
        self.event = Event()
        self.known = []
        self.caxton_token = caxton_token
 
    def start(self):
        self.thread.start()
 
    def stop(self):
        # This is a neat trick to make thread end. Took me a 
        # while to figure that one out!
        self.event.set()
 
    def join(self):
        self.thread.join()
 
    def idle(self):
        # Starting an unending loop here
        while True:
            # This is part of the trick to make the loop stop 
            # when the stop() command is given
            if self.event.isSet():
                return
            self.needsync = False
            # A callback method that gets called when a new 
            # email arrives. Very basic, but that's good.
            def callback(args):
                if not self.event.isSet():
                    self.needsync = True
                    self.event.set()
            # Do the actual idle call. This returns immediately, 
            # since it's asynchronous.
            self.M.idle(callback=callback)
            # This waits until the event is set. The event is 
            # set by the callback, when the server 'answers' 
            # the idle call and the callback function gets 
            # called.
            self.event.wait()
            # Because the function sets the needsync variable,
            # this helps escape the loop without doing 
            # anything if the stop() is called. Kinda neat 
            # solution.
            if self.needsync:
                self.event.clear()
                self.dosync()
 
    # The method that gets called when a new email arrives. 
    # Replace it with something better.
    def dosync(self):
        (retcode, messages) = self.M.search(None, '(UNSEEN)')
        if retcode == 'OK':
            for num in messages[0].split(' '):
                if num in self.known:
                    print "Already handled", num
                    continue

                self.known.append(num)
                print 'Processing :', num
                typ, data = self.M.fetch(num,'(RFC822.HEADER)')
                msg = email.message_from_string(data[0][1])
                line = "New message from %(from)s about %(subject)s" % msg
                urllib.urlopen("https://caxton.herokuapp.com/api/send",
                    data=urllib.urlencode({
                        "url": config.url,
                        "appname": APPNAME,
                        "token": self.caxton_token,
                        "message": line
                    })
                )
                print "Sent", line

if not hasattr(config, "caxton_token") or not config.caxton_token:
    print "You need to pair this daemon with Caxton."
    print ("Press the 'Get a code' button in the Caxton app on your phone,")
    code = raw_input("and enter the code it gives: ")
    fp = urllib.urlopen("https://caxton.herokuapp.com/api/gettoken", 
        data=urllib.urlencode({"code": code, "appname": APPNAME}))
    data = fp.read()
    try:
        j = json.loads(data)
    except:
        print "Failed to get a token (the Caxton server said: %s)" % (data,)
        sys.exit(1)
    token = j.get("token")
    if not token:
        print "Failed to get a token (the Caxton server said: %s)" % (data,)
        sys.exit(1)
    print "Saving token in config.py..."
    fp = open("config.py", "a")
    fp.write("\ncaxton_token='%s'\n" % token)
    fp.close()
else:
    token = config.caxton_token

# Had to do this stuff in a try-finally, since some testing 
# went a little wrong.....
print "Connecting to IMAP server."
try:
    # Set the following two lines to your creds and server
    M = imaplib2.IMAP4_SSL(config.mailserver)
    M.login(config.username, config.password)
    # We need to get out of the AUTH state, so we just select 
    # the INBOX.
    M.select("INBOX")
    # Start the Idler thread
    idler = Idler(M, token)
    idler.start()
    # Because this is just an example, exit after 1 minute.
    while 1:
        time.sleep(1*60)
finally:
    # Clean up.
    idler.stop()
    idler.join()
    M.close()
    # This is important!
    M.logout()
