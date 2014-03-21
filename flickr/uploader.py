import flickrapi
import pickle
import os
import tarfile
import re
import xml.etree.ElementTree as etree

picture_dir = '/hkn/bridge/flickr/pictures'
backup_dir = '/hkn/bridge/flickr/backup'
auth_url_file = 'auth_url.txt'
uploaded_filename = 'uploaded.pkl'
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

def new_directories():
    """Return a list of directories that did not exist the
    last time we checked.
    """
    if not os.path.isfile(uploaded_filename):
        uploaded = set()
    else:
        with open(uploaded_filename) as f:
            uploaded = pickle.load(f)

    new_dirs = []
    for dirpath, dirnames, filenames in os.walk(picture_dir):
        for dirname in dirnames:
            subdir_path = os.path.join(dirpath, dirname)
            if subdir_path in uploaded:
                continue

            print "Found new directory: %s" % subdir_path
            new_dirs.append(subdir_path)
            uploaded.add(subdir_path)

    with open(uploaded_filename, 'w') as f:
        pickle.dump(uploaded, f)

    return new_dirs

def upload_new():
    """Walks the pictures directory and uploads all new directories.
    Also saves them as tarballs.
    """
    dirs = new_directories()
    for directory in dirs:
        photo_ids = []
        for filename in os.listdir(directory):
            if not is_image(filename):
                continue
            photo_ids.append(upload_file(directory, filename))
        if len(photo_ids) == 0:
            continue

        save_tar(directory)

        dir_name = os.path.relpath(directory, picture_dir)
        dir_name = '_'.join(dir_name.split('/'))
        make_photoset(photo_ids, dir_name)

def make_photoset(photo_ids, title):
    """Given a list of photo IDs, makes a photoset titled TITLE
    containing those photos.
    """
    result = flickr.photosets_create(
        title = title, description = title,
        primary_photo_id = photo_ids[0])
    for child in result:
        if child.tag == 'photoset':
            photoset_id = child.attrib['id']

    for photoid in photo_ids[1:]:
        flickr.photosets_addPhoto(photoset_id = photoset_id, photo_id = photoid)

def save_tar(directory):
    """Compresses DIRECTORY into a tarball and saves it in the backup
    directory.
    """
    dir_name = os.path.relpath(directory, picture_dir)
    backup_path = os.path.join(backup_dir, dir_name + '.tar.gz')
    backup_subdir = os.path.dirname(backup_path)
    if not os.path.exists(backup_subdir):
        os.makedirs(backup_subdir)

    tar = tarfile.open(backup_path, 'w:gz')
    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        tar.add(path, recursive = False)
    tar.close()

def upload_file(directory, filename):
    """Uploads file/directory with name FILENAME in
    DIRECTORY to Flickr.
    """
    path = os.path.join(directory, filename)
    result = flickr.upload(path,
        title = filename,
        description = filename)
    for child in result:
        if child.tag == 'photoid':
            photoid = child.text

    print "Uploaded %s with ID %s" % (filename, photoid)
    return photoid

api_key, api_secret = load_keys()
flickr = authenticate()
upload_new()
