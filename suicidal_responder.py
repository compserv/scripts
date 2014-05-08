import sys
import email
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.message import MIMEMessage

import random
import string
random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))

suicidal_confirm = ("Before you're added to the suicidal mailing list, we'd like to "
                    "remind you that suicidal gets emails sent to EVERY committee. "
                    "If you're interested in getting emails for a specific committee, "
                    "we could add you as an auditor for that committee mailing list."
                    "\n\n"
                    "Additionally, during a time of transition like post elections "
                    "there is an especially large volume of emails sent for each "
                    "committee and therefore it may be desirable to wait out this "
                    "period before being added to suicidal."
                    "\n\n"
                    "If you would still like to be added to suicidal, please respond "
                    "with 'YES, I, " + random_string + ", WOULD LIKE TO BE ADDED.'")

if __name__ == "__main__":
    msg = email.message_from_file(sys.stdin)
    subject = msg["subject"]
    sender = msg["from"]
    me = "ops@hkn.eecs.berkeley.edu"

    new_msg = MIMEMultipart("alternative")
    new_msg.attach(MIMEText(suicidal_confirm, "plain", "UTF-8"))
    new_msg["Subject"] = "Re: {0}".format(subject)
    new_msg["From"] = me
    new_msg["To"] = sender
    new_msg["Cc"] = "compserv@hkn.eecs.berkeley.edu, ops@hkn.eecs.berkeley.edu"
    new_msg["In-Reply-To"] = msg["Message-ID"]
    new_msg["References"] = msg["Message-ID"]

    s = smtplib.SMTP("localhost")
    s.sendmail(me, [sender], new_msg.as_string())
    s.quit()


