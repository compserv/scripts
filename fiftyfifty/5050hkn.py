#!/usr/bin/env python
import praw, random, os, re, pickle

#Mail command file
MAIL_COMMAND_FILENAME = '/hkn/compserv/scripts/fiftyfifty/mail_command.txt'
#Already-sent file
SENT_FILENAME = '/hkn/compserv/scripts/fiftyfifty/sent.pkl'
#Weights for choosing each subreddit
WEIGHTS = {
    'awwnime': 0.5,
    'ecchi': 0.2,
    'pantsu': 0.1,
    'animewallpaper': 0.1,
    'sukebei': 0.05,
    'animenocontext': 0.05
    }
#Message to send for each subreddit
MESSAGES = {
    'awwnime': "Aww, it's awwnime...",
    'ecchi': "Ew, it's ecchi...",
    'pantsu': "P is for... pantservice...",
    'animewallpaper': "Woo, it's an (ecchi) wallpaper...",
    'sukebei': "Surprise, it's sukebei...",
    'animenocontext': "Animenocontext. Wat..."
    }

def send_email(url, msg):
    """Send an email with image url URL and message MSG.
    """
    with open(MAIL_COMMAND_FILENAME) as f:
        command = f.read()
        command = command % (msg, url)
    os.system(command)

def valid_url(url):
    """Return True if URL is a valid image URL.
    """
    url = url.lower()
    valid_extensions = ['png', 'jpg', 'jpeg', 'bmp', 'gif']
    match = re.match('.+\\.(.+)', url)
    if not match:
        return False
    extension = match.group(1)
    if 'imgur' not in url:
	return False
    return extension in valid_extensions

def get_sent():
    """Loads a set of sent photos.
    """
    if not os.path.isfile(SENT_FILENAME):
        return set(['http://i.imgur.com/VZ955MB.jpg'])

    with open(SENT_FILENAME) as f:
        return pickle.load(f)

def save_sent(sent_set, url):
    sent_set.add(url)
    with open(SENT_FILENAME, 'w') as f:
        pickle.dump(sent_set, f)

def main():
    #Choose subreddit
    rand = random.random()
    for sub, weight in WEIGHTS.items():
        if rand <= weight:
            subreddit = sub
            break
        rand -= weight
    message = MESSAGES[subreddit]

    #Get first valid submission
    reddit = praw.Reddit(user_agent='hkn')
    submissions = reddit.get_subreddit(subreddit).get_top_from_month(limit=30)
    submissions = sorted(list(submissions), key = lambda s: -s.score)
    if subreddit == 'animewallpaper':
        submissions = [s for s in submissions if s.over_18]
    urls = [s.url for s in submissions]
    valid_urls = [u for u in urls if valid_url(u)]

    sent_set = get_sent()
    valid_urls = [url for url in valid_urls if url not in sent_set]

    url = valid_urls[0]
    send_email(url, message)
    save_sent(sent_set, url)

main()
