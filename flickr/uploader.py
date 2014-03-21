import flickrapi
import pickle
import os
import tarfile

picture_dir = '/home/josephhui/flickr/pictures'
backup_dir = '/home/josephhui/flickr/backup'
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

            print subdir_path
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
        for filename in os.listdir(directory):
            upload_file(directory, filename)
        save_tar(directory)

def save_tar(directory):
    """Compresses DIRECTORY into a tarball and saves it in the backup
    directory.
    """
    dir_name = os.path.relpath(directory, picture_dir)
    backup_path = os.path.join(backup_dir, dir_name + '.tar.gz')
    tar = tarfile.open(backup_path, 'w:gz')
    tar.add(directory)
    tar.close()

def upload_file(directory, filename):
    """Uploads file/directory with name FILENAME in
    DIRECTORY to Flickr.
    """
    path = os.path.join(directory, filename)
    flickr.upload(path,
        title = filename,
        description = "An awesome picture")
    print "Uploading %s" % filename

api_key, api_secret = load_keys()
flickr = authenticate()
upload_new()

