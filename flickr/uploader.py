import flickrapi
import pickle
import os
import tarfile
import re
import urllib2
import xml.etree.ElementTree as etree

picture_dir = '/hkn/bridge/flickr/pictures'
backup_dir = '/hkn/bridge/flickr/backup'
auth_url_file = 'auth_url.txt'
uploaded_filename = 'uploaded.pkl'
photosets_filename = 'photosets.pkl'
key_dir = 'keys'

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

def new_files():
    """Return a list of new files and a list of changed
    directories (directories with new files).

    Files are returned as absolute paths.
    """
    uploaded = unpickle_from(uploaded_filename, set())

    new_files = []
    for dirpath, dirnames, filenames in os.walk(picture_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if file_path in uploaded:
                continue

            #print "Found new file: %s" % file_path
            new_files.append(file_path)
            uploaded.add(file_path)

    with open(uploaded_filename, 'w') as f:
        pickle.dump(uploaded, f)

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
    photosets = unpickle_from(photosets_filename, {})
    files = new_files()

    bad_events = set()
    for file_path in files:
        if not is_image(file_path):
            continue
        bad_event = upload_file(photosets, file_path)
        if bad_event:
            bad_events.add(bad_event)

    if len(bad_events) > 0:
        print "Bad events: %s" % bad_events
        send_email(bad_events)

    with open(photosets_filename, 'w') as f:
        pickle.dump(photosets, f)

def insert_photoset(photosets, set_name, photo_id):
    """Given an photoset name SET_NAME and a mapping PHOTOSETS from
    directory to photoset id, puts the photo with id PHOTO_ID in the
    appropriate photoset, creating it if necessary.
    """
    if set_name in photosets:
        photoset_id = photosets[set_name]
        retry(flickr.photosets_addPhoto, "Photoset add",
            photoset_id = photoset_id, photo_id = photo_id)
    else:
        result = retry(flickr.photosets_create, "Create photoset",
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
    """Attempts to call FN with arguments KWARGS 10 times.
    Reports errors describing the operation with NAME.
    """
    retries = 10
    while retries > 0:
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            print '%s error: %s' % (name, e)
            retries -= 1

    print 'Out of retries. Exiting.'

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
    command += ' | mail -s "Bad event name" current-bridge@hkn.eecs.berkeley.edu'
    os.system(command)

def upload_file(photosets, file_path):
    """Uploads file/directory with absolute path FILE_PATH to Flickr
    and puts it in an appropriate photoset, given the set of existing
    photosets PHOTOSETS. Also tags it.

    If the event name is not valid, return the event name. Otherwise return None.

    E.g.: upload_file(set(), '/hkn/bridge/flickr/pictures/Sp14/0304-Potluck/pic.jpg')
    """
    directory, filename = os.path.split(file_path)
    if first_dirs(directory) is None:
        return
    semester, event = first_dirs(directory)
    event = ''.join(event.split())
    if not re.match("\d\d\d\d-[a-zA-Z0-9]+\Z", event):
        return event

    result = retry(flickr.upload, 'Upload',
        file_path, title = filename, description = filename)

    photoid_elt = [c for c in result if c.tag == 'photoid'][0]
    photoid = photoid_elt.text

    print 'Uploaded %s with ID %s' % (filename, photoid)

    if event[:4] == '0000':
        photoset_name = '-'.join([semester, event[5:]])
    else:
        photoset_name = '-'.join([semester, event])
    insert_photoset(photosets, photoset_name, photoid)

    event = event[5:]
    tags = ' '.join([semester, event])
    retry(flickr.photos_setTags, 'Tags',
        photo_id = photoid, tags = tags)

api_key, api_secret = load_keys()
flickr = authenticate()
upload_new()