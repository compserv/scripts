import boto
import boto.glacier
import time
import sys

ID_FILE = "AWSCredentials.awsid"
SECRET_KEY_FILE = "AWSCredentials.awskey"

with open(ID_FILE) as id_file:
    ACCESS_KEY_ID = id_file.read()

with open(SECRET_KEY_FILE) as secret_key_file:
    SECRET_ACCESS_KEY = secret_key_file.read()

def connect():
    """Connect to our Amazon Glacier account and return
    the vault.
    """
    glacier_connection = boto.glacier.connect_to_region(
        "us-west-2",
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY)
    return glacier_connection.get_vault("testing")

def upload(filename):
    """Upload the file specified by FILENAME to Amazon
    Glacier and return the archive ID.
    """
    vault = connect()
    archive_id = vault.upload_archive(filename)
    print(time.asctime() + ": ID " + str(archive_id))

def start_job(archive_id):
    """Start a job to download the file specified by
    ARCHIVE_ID and print the resulting job ID.
    """
    vault = connect()
    job = vault.retrieve_archive(archive_id)
    print("Job initiated with job ID " + str(job.id))

def download(job_id, filename):
    """Attempt to download the data from the job specified
    by JOB_ID to the file FILENAME. Print success/failure
    message.
    """
    job = vault.get_job(job_id)

    if job.completed:
        job.download_to_file(filename)
        print("File successfully downloaded.")
    else:
        print("Job not completed.")

if __name__ == "__main__":
    arg1 = sys.argv[1]
    if (arg1 == "--start"):
        start_job(sys.argv[2])
    elif (arg1 == "--download"):
        download(sys.argv[2])
    else:
        upload(sys.argv[1])

