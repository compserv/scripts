import sys, random, string

import email, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.message import MIMEMessage

MESSAGE_FILE = 'suicidal_message.txt'

random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
with open(MESSAGE_FILE) as f:
    suicidal_confirm = f.read().format(random_string)

if __name__ == "__main__":
    msg = email.message_from_file(sys.stdin)
    subject = msg["subject"]
    sender = msg["from"]
    me = "ops@hkn.eecs.berkeley.edu"
    cc = ["compserv@hkn.eecs.berkeley.edu", "ops@hkn.eecs.berkeley.edu"]

    new_msg = MIMEMultipart("alternative")
    new_msg.attach(MIMEText(suicidal_confirm, "plain", "UTF-8"))
    new_msg["Subject"] = "Re: {0}".format(subject)
    new_msg["From"] = me
    new_msg["To"] = sender
    new_msg["Cc"] = ",".join(cc) 
    new_msg["In-Reply-To"] = msg["Message-ID"]
    new_msg["References"] = msg["Message-ID"]

    toaddrs = [sender] + cc

    s = smtplib.SMTP("localhost")
    s.sendmail(me, toaddrs, new_msg.as_string())
    s.quit()
