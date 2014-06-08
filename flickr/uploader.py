import flickrapi
import os, pickle, time, tarfile
import re, urllib2, imghdr
import xml.etree.ElementTree as etree
import smtplib
from email.mime.text import MIMEText

PICTURE_DIR = '/hkn/bridge/flickr/pictures'
AUTH_URL_FILE = 'auth_url.txt'
MESSAGE_FILE = 'message.txt'
UPLOADED_FILENAME = 'uploaded.pkl'
PHOTOSETS_FILENAME = 'photosets.pkl'
KEY_DIR = 'keys'

COMPSERV_EMAIL = 'compserv@hkn.eecs.berkeley.edu'
BRIDGE_EMAIL = 'current-bridge@hkn.eecs.berkeley.edu'

#Number of times to retry an operation
MAX_RETRIES = 5
#Initial delay before retrying (doubles each retry)
INITIAL_RETRY_DELAY = 0.03

def load_keys():
    """Loads api key/secret from file."""
    with open(os.path.join(KEY_DIR, 'api_key')) as f:
        api_key = f.read()
    with open(os.path.join(KEY_DIR, 'api_secret')) as f:
        api_secret = f.read()
    return api_key, api_secret

def authenticate(api_key, api_secret):
    """Authenticates the application. Asks user to authenticate
    if token not already stored.
    """
    flickr = flickrapi.FlickrAPI(api_key, api_secret)

    def authenticate_link(frob, perms):
        """Prints a link to authorize the app and waits 60
        seconds for authorization.
        """
        import time
        auth_url = flickr.auth_url(perms, frob)
        with open(AUTH_URL_FILE, 'w') as f:
            f.write(auth_url)
        print("Please authorize at the URL in {}".format(AUTH_URL_FILE))
        print("Continuing in 60 seconds.")
        time.sleep(60)

    (token, frob) = flickr.get_token_part_one(
        perms = 'write', auth_callback = authenticate_link)

    flickr.get_token_part_two((token, frob))
    return flickr

def is_image(filename):
    """Returns True iff FILENAME looks like a valid image."""
    return imghdr.what(filename) is not None

def new_files(uploaded):
    """Return a list of new images.
    Files are returned as absolute paths.

    UPLOADED: Already-uploaded filepaths.
    """
    new_files = []
    for dirpath, dirnames, filenames in os.walk(PICTURE_DIR):
        for filename in filenames:
            if not is_image(filename):
                continue
            file_path = os.path.join(dirpath, filename)
            if file_path in uploaded:
                continue

            new_files.append(file_path)

    return new_files

def unpickle_from(filename, default):
    """If FILENAME exists, unpickle and return an object from it.
    Otherwise return DEFAULT.
    """
    if not os.path.isfile(filename):
        return default

    with open(filename) as f:
        return pickle.load(f)

def upload_new():
    """Walks the pictures directory and uploads all new files.
    Also saves changed directories as tarballs.
    """
    start = time.clock()
    uploaded = unpickle_from(UPLOADED_FILENAME, set())
    uploaded = set(uploaded)
    photosets = unpickle_from(PHOTOSETS_FILENAME, {})
    files = new_files(uploaded)

    bad_events = set()
    for file_path in files:
        try:
            bad_event = upload_file(flickr, photosets, uploaded, file_path)
            if bad_event:
                bad_events.add(bad_event)
        except RetryException:
            print "Okay, moving on."

        if time.clock() - start > (60 * 60 * 12):
            break

    if len(bad_events) > 0:
        print "Bad events: {}".format(bad_events)
        send_email(bad_events)

    with open(PHOTOSETS_FILENAME, 'w') as f:
        pickle.dump(photosets, f)
    with open(UPLOADED_FILENAME, 'w') as f:
        pickle.dump(uploaded, f)

def insert_photoset(flickr, photosets, set_name, photo_id):
    """Given an photoset name SET_NAME and a mapping PHOTOSETS from
    directory to photoset id, puts the photo with id PHOTO_ID in the
    appropriate photoset, creating it if necessary.
    """
    if set_name in photosets:
        photoset_id = photosets[set_name]
        retry(flickr.photosets_addPhoto, "Photoset add {}".format(photo_id),
            photoset_id = photoset_id, photo_id = photo_id)
    else:
        result = retry(flickr.photosets_create,
            "Create photoset {}".format(photo_id),
            title = set_name, description = set_name,
            primary_photo_id = photo_id)
        ps_element = [c for c in result if c.tag == 'photoset'][0]
        photoset_id = ps_element.attrib['id']
        photosets[set_name] = photoset_id

def first_dirs(directory):
    """Returns the first two directories from the relative path of
    DIRECTORY from the pictures directory. Returns None if the path
    does not contain at least two directories.

    >>> first_dirs('/hkn/bridge/flickr/pictures/sp14/event/subdirectory')
    ('sp14', 'event')
    >>> first_dirs('/hkn/bridge/flickr/pictures/sp14/event')
    ('sp14', 'event')
    >>> print(first_dirs('/hkn/bridge/flickr/pictures/sp14'))
    None
    """
    directory = os.path.relpath(directory, PICTURE_DIR)
    directories = []
    while directory != '':
        directory, last = os.path.split(directory)
        directories.append(last)

    if len(directories) < 2:
        return None

    return (directories[-1], directories[-2])

def retry(fn, name, *args, **kwargs):
    """Call FN with arguments ARGS/KWARGS repeatedly, with an
    exponential backoff after each failure.

    Report errors describing the operation with NAME.
    If we run out of retries, raise a RetryException.
    """
    retries = MAX_RETRIES
    delay = INITIAL_RETRY_DELAY

    while retries > 0:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print '{}: {} error: {} {}.'.format(time.asctime(), name, type(e), e)
            time.sleep(delay)
            retries -= 1
            delay *= 2

    print 'Out of retries for {}.'.format(name)
    raise RetryException()

def send_email(bad_events):
    """Send an email to current-bridge@hkn.eecs.berkeley.edu complaining
    about bad event names.
    """
    with open(MESSAGE_FILE) as f:
        message_text = f.read().format('\n'.join(bad_events))

    msg = MIMEText(message_text)
    msg['Subject'] = 'Bad event names'
    msg['From'] = COMPSERV_EMAIL
    msg['To'] = BRIDGE_EMAIL

    s = smtplib.SMTP('localhost')
    s.sendmail(COMPSERV_EMAIL, [BRIDGE_EMAIL], msg.as_string())
    s.quit()

def upload_file(flickr, photosets, uploaded, file_path):
    """Uploads file/directory with absolute path FILE_PATH to Flickr
    and puts it in an appropriate photoset, given the dict of existing
    photosets PHOTOSETS. Also tags it.

    If upload is successful, adds filepath to UPLOADED.
    Returns the event name if it was invalid; otherwise None.

    If network fails and we run out of retries, an Exception will be raised.

    Events titled '0000-someevent' have the '0000-' ignored.

    E.g.: upload_file({}, set(), '/hkn/bridge/flickr/pictures/Sp14/0304-Potluck/pic.jpg')
    """
    directory, filename = os.path.split(file_path)
    if first_dirs(directory) is None:
        return
    semester, event = first_dirs(directory)
    event = ''.join(event.split())
    if not re.match("\d\d\d\d-[a-zA-Z0-9]+\Z", event):
        return event

    result = retry(flickr.upload, 'Upload {}'.format(filename),
        file_path, title = filename, description = filename)

    photoid_elt = [c for c in result if c.tag == 'photoid'][0]
    photoid = photoid_elt.text

    if event[:4] == '0000':
        photoset_name = '-'.join([semester, event[5:]])
    else:
        photoset_name = '-'.join([semester, event])
    insert_photoset(flickr, photosets, photoset_name, photoid)

    event = event[5:]
    tags = ' '.join([semester, event])
    retry(flickr.photos_setTags, 'Tag {}'.format(photoid),
        photo_id = photoid, tags = tags)

    uploaded.add(file_path)

def sort_sets(flickr):
    """Sorts photosets by semester."""
    #name => id
    photosets = unpickle_from(PHOTOSETS_FILENAME, {})
    print len(photosets)

    def date(set_name):
        set_name = set_name.upper()
        semesters = {'SP': 0, 'FA': 0.5}
        if set_name[:2] in semesters:
            year = set_name[2:4]
            date = int(year)
            if year[0] != '9':
                date += 100
            date += semesters[set_name[:2]]
        elif set_name[:3] == 'OLD':
            date = -10
        else:
            print 'wat: {}'.format(set_name)
            date = -20
        return -date

    photosets = list(photosets.items())
    photosets.sort(key = lambda kv: date(kv[0]))
    sorted_ids = ','.join([kv[1] for kv in photosets])

    flickr.photosets_orderSets(photoset_ids = sorted_ids)

def fetch_photosets(flickr):
    """Update photosets with data from website."""
    photosets = unpickle_from(PHOTOSETS_FILENAME, {})
    result = flickr.photosets_getList()
    photosets_element = [c for c in result if c.tag == 'photosets'][0]

    missing = 0
    for ps_element in photosets_element:
        ps_id = ps_element.attrib['id']
        title = [c for c in ps_element if c.tag == 'title'][0].text
        if title not in photosets:
            photosets[title] = ps_id
            missing += 1
    print missing

    with open(PHOTOSETS_FILENAME, 'w') as f:
        pickle.dump(photosets, f)

class RetryException(Exception):
    pass

if __name__ == '__main__':
    api_key, api_secret = load_keys()
    flickr = authenticate(api_key, api_secret)
    upload_new(flickr)
