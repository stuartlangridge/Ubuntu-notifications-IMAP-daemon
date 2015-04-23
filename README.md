# IMAP Push notifications for Ubuntu phone

A simple daemon. Rename `config.py.example` to `config.py` and edit it to have your mail details in, and the URL you want to open on the phone (for webmail, or an app-specific custom URL scheme to open a particular app). Run it on a permanently-on server of your choice with "python daemon.py".
It will pair with the Caxton app on your phone, and then monitor your email account (with IMAP IDLE) and send a notification when you get new mail. No waiting for the phone to poll any more!

