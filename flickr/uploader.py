import flickrapi
import os, pickle, time, tarfile
import re, urllib2
import xml.etree.ElementTree as etree

picture_dir = '/hkn/bridge/flickr/pictures'
backup_dir = '/hkn/bridge/flickr/backup'
auth_url_file = 'auth_url.txt'
uploaded_filename = 'uploaded.pkl'
photosets_filename = 'photosets.pkl'
key_dir = 'keys'
UPLOAD_QUOTA = 4000 #Maximum number of files to upload in a session

def load_keys():
    """Loads api key/secret from file.
    """
    with open(os.path.join(key_dir, 'api_key')) as f:
        api_key = f.read()
    with open(os.path.join(key_dir, 'api_secret')) as f:
        api_secret = f.read()
    return api_key, api_secret

def authenticate():
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
        with open(auth_url_file, 'w') as f:
            f.write(auth_url)
        print("Please authorize at the URL in %s" % auth_url_file)
        print("Continuing in 60 seconds.")
        time.sleep(60)

    (token, frob) = flickr.get_token_part_one(
        perms = 'write', auth_callback = authenticate_link)

    flickr.get_token_part_two((token, frob))
    return flickr

def is_image(filename):
    """Returns True iff FILENAME looks like a valid image name.
    """
    valid_extensions = ['png', 'jpg', 'jpeg', 'bmp', 'gif']

    filename = filename.lower()
    match = re.match('.+\\.(.+)', filename)
    if not match:
        return False
    extension = match.group(1)

    return extension in valid_extensions

def new_files(uploaded):
    """Return a list of new images.
    Files are returned as absolute paths.

    UPLOADED: Already-uploaded filepaths.
    """
    new_files = []
    for dirpath, dirnames, filenames in os.walk(picture_dir):
        for filename in filenames:
            if not is_image(filename):
                continue
            file_path = os.path.join(dirpath, filename)
            if file_path in uploaded:
                continue

            new_files.append(file_path)

    return new_files[:UPLOAD_QUOTA]

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
    uploaded = unpickle_from(uploaded_filename, set())
    uploaded = set(uploaded)
    photosets = unpickle_from(photosets_filename, {})
    files = new_files(uploaded)

    bad_events = set()
    for file_path in files:
        try:
            bad_event = upload_file(photosets, uploaded, file_path)
            if bad_event:
                bad_events.add(bad_event)
        except RetryException:
            print "Okay, moving on."

        if time.clock() - start > (60 * 60 * 12):
            break

    if len(bad_events) > 0:
        print "Bad events: %s" % bad_events
        send_email(bad_events)

    with open(photosets_filename, 'w') as f:
        pickle.dump(photosets, f)
    with open(uploaded_filename, 'w') as f:
        pickle.dump(uploaded, f)

def insert_photoset(photosets, set_name, photo_id):
    """Given an photoset name SET_NAME and a mapping PHOTOSETS from
    directory to photoset id, puts the photo with id PHOTO_ID in the
    appropriate photoset, creating it if necessary.
    """
    if set_name in photosets:
        photoset_id = photosets[set_name]
        retry(flickr.photosets_addPhoto, "Photoset add %s" % photo_id,
            photoset_id = photoset_id, photo_id = photo_id)
    else:
        result = retry(flickr.photosets_create,
            "Create photoset %s" % photo_id,
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
    directory = os.path.relpath(directory, picture_dir)
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
    retries = 5
    delay = 0.03 #Initial delay in seconds

    while retries > 0:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print '%s: %s error: %s %s.' % (time.asctime(), name, type(e), e)
            time.sleep(delay)
            retries -= 1
            delay *= 2

    print 'Out of retries for %s.' % name
    raise RetryException()

def send_email(bad_events):
    """Send an email to current-bridge@hkn.eecs.berkeley.edu complaining
    about bad event names.
    """
    message = "Hi Bridge,\\n\\n"
    message += "This is your humble servant, FlickrBot. I regret to inform you that "
    message += "some of the events in the flickr/pictures directory are not correctly "
    message += "formatted. As a reminder, the correct format is:\\n"
    message += "MMDD-CAMELCASEDEVENTNAME\\n"
    message += "E.g. flickr/pictures/Sp14/0307-CandidateIceCream.\\n\\n"
    message += "The following directories are incorrectly formatted:\\n"
    for event in bad_events:
        message += event + "\\n"
    message += "\\nPlease rename these directories. They will be uploaded "
    message += "the next time I am activated.\\n\\n"
    message += "Forever loyal,\\n"
    message += "FlickrBot"

    command = 'echo "' + message + '"'
    command += ' | mail -s "Bad event name" '
    command += 'compserv@hkn.eecs.berkeley.edu current-bridge@hkn.eecs.berkeley.edu'
    os.system(command)

def upload_file(photosets, uploaded, file_path):
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

    result = retry(flickr.upload, 'Upload %s' % filename,
        file_path, title = filename, description = filename)

    photoid_elt = [c for c in result if c.tag == 'photoid'][0]
    photoid = photoid_elt.text

    if event[:4] == '0000':
        photoset_name = '-'.join([semester, event[5:]])
    else:
        photoset_name = '-'.join([semester, event])
    insert_photoset(photosets, photoset_name, photoid)

    event = event[5:]
    tags = ' '.join([semester, event])
    retry(flickr.photos_setTags, 'Tag %s' % photoid,
        photo_id = photoid, tags = tags)

    uploaded.add(file_path)

def sort_sets():
    """Sorts photosets by semester.
    """
    #name => id
    photosets = unpickle_from(photosets_filename, {})
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
            print 'wat: %s' % set_name
            date = -20
        return -date

    photosets = list(photosets.items())
    photosets.sort(key = lambda kv: date(kv[0]))
    sorted_ids = ','.join([kv[1] for kv in photosets])

    flickr.photosets_orderSets(photoset_ids = sorted_ids)

def fetch_photosets():
    """Update photosets with data from website.
    """
    photosets = unpickle_from(photosets_filename, {})
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

    with open(photosets_filename, 'w') as f:
        pickle.dump(photosets, f)

class RetryException(Exception):
    pass

api_key, api_secret = load_keys()
flickr = authenticate()
if __name__ == '__main__':
    #fetch_photosets()
    #sort_sets()
    upload_new()