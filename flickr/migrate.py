import csv, re, os, shutil

csv_file = '/hkn/compserv/django_gallery_dump.csv'
photologue_dir = '/var/www/hkn/files/photologue/photos'
flickr_dir = '/hkn/bridge/flickr/pictures'

def normalize(name):
    """Normalizes semester name.
    >>> normalize('20080801__SEMESTER__fa08')
    Fa08
    """
    semester = name[-4:]
    if not re.match('\w\w\d\d', semester):
        print "Weird semester name: %s" % name
    semester = semester[0].upper() + semester[1:].lower()
    return semester

def dirname(event):
    """Normalizes event name.
    >>> dirname('Ice Cream Social')
    '0000-IceCreamSocial'
    """
    event = ''.join(c for c in event if c.isalnum())
    event = '0000-' + event
    return event

def ensure_path(filepath):
    """Ensure that the directory containing FILEPATH exists.
    """
    directory, filename = os.path.split(filepath)
    if not os.path.isdir(os.path.split(directory)[0]):
        ensure_path(directory)
    if not os.path.isdir(directory):
        os.mkdir(directory)

def migrate():
    events = set()
    with open(csv_file) as f:
        reader = csv.reader(f)
        for row in reader:
            semester, event, desc, tags, public, url = row

            semester = normalize(semester)
            file_loc = os.path.relpath(url, 'photologue/photos')
            event = dirname(event)

            if semester not in ['Sp09', 'Fa09', 'Fa08']:
                continue

            semester_dir = os.path.join(flickr_dir, semester)
            event_dir = os.path.join(semester_dir, event)

            src = os.path.join(photologue_dir, file_loc)
            dest = os.path.join(event_dir, file_loc)
            if not os.path.isfile(src):
                print "Missing: %s" % ((src, url, file_loc),)

            ensure_path(dest)
            shutil.copy(src, dest)

migrate()