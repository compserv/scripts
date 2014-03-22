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
    """
    uploaded = unpickle_from(uploaded_filename, set())

    changed_dirs = set()
    new_files = []
    for dirpath, dirnames, filenames in os.walk(picture_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if file_path in uploaded:
                continue

            print "Found new file: %s" % file_path
            new_files.append(file_path)
            uploaded.add(file_path)
            changed_dirs.add(dirpath)

    with open(uploaded_filename, 'w') as f:
        pickle.dump(uploaded, f)

    print "Changed directories: %s" % changed_dirs
    return new_files, changed_dirs

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
    files, dirs = new_files()

    for file_path in files:
        if not is_image(file_path):
            continue
        upload_file(photosets, file_path)

    for directory in dirs:
        save_tar(directory)

    with open(photosets_filename, 'w') as f:
        pickle.dump(photosets, f)

def insert_photoset(photosets, file_dir, photo_id):
    """Given a photo FILENAME and a mapping PHOTOSETS from directory to
    photoset id, puts the photo with id PHOTO_ID in the appropriate
    photoset, creating it if necessary.
    """
    dir_name = os.path.relpath(file_dir, picture_dir)
    dir_name = '_'.join(dir_name.split('/'))

    if file_dir in photosets:
        photoset_id = photosets[file_dir]
        flickr.photosets_addPhoto(photoset_id = photoset_id, photo_id = photo_id)
    else:
        result = flickr.photosets_create(
            title = dir_name, description = dir_name,
            primary_photo_id = photo_id)
        ps_element = [c for c in result if c.tag == 'photoset'][0]
        photoset_id = ps_element.attrib['id']
        photosets[file_dir] = photoset_id

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

def upload_file(photosets, file_path):
    """Uploads file/directory with name FILENAME in
    DIRECTORY to Flickr and puts it in an appropriate photoset.
    """
    directory, filename = os.path.split(file_path)
    retries = 10
    while retries > 0:
        try:
            result = flickr.upload(file_path,
                title = filename,
                description = filename)
            break
        except Exception as e:
            print "Upload error: %s" % e
    if retries == 0:
        print "Failed to upload file %s" % filename
        return

    photoid_elt = [c for c in result if c.tag == 'photoid'][0]
    photoid = photoid_elt.text

    print "Uploaded %s with ID %s" % (filename, photoid)
    insert_photoset(photosets, directory, photoid)

api_key, api_secret = load_keys()
flickr = authenticate()
upload_new()
