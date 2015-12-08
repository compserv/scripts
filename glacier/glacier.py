import boto3
import time
import sys

ID_FILE = "AWSCredentials.awsid"
SECRET_KEY_FILE = "AWSCredentials.awskey"
VAULT_NAME = "dbbackups"
RETRIES = 10 #Number of times to retry uploading

with open(ID_FILE) as id_file:
    ACCESS_KEY_ID = id_file.read()

with open(SECRET_KEY_FILE) as secret_key_file:
    SECRET_ACCESS_KEY = secret_key_file.read()

def connect():
    """Connect to our Amazon Glacier account and return
    the client.
    """
    return boto3.client('glacier',
        "us-west-2",
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY)

def upload(filename):
    """Upload the file specified by FILENAME to Amazon
    Glacier and return the archive ID.
    """
    client = connect()
    for _ in range(RETRIES):
        archive_id = client.upload_archive(
            vaultName=VAULT_NAME,
            archiveDescription=str(time.asctime()),
            body=open(filename))
        print(time.asctime() + ": ID " + str(archive_id))
        return

def delete_archive(archive_id):
    client = connect()
    client.delete_archive(
        vaultName=VAULT_NAME,
        archiveId=archive_id)
    print('Deleted ' + archive_id)

def delete_all(filename):
    with open(filename) as f:
        for line in f:
            delete_archive(line.split()[-1])

def start_job(archive_id):
    """Start a job to download the file specified by
    ARCHIVE_ID and print the resulting job ID.
    """
    client = connect()
    response = client.initiate_job(
        vaultName=VAULT_NAME,
        jobParameters={
            'Type': 'archive-retrieval',
            'ArchiveId': str(archive_id)
        })
    print("Job initiated with job ID " + response['jobId'])

def download(job_id, filename):
    """Attempt to download the data from the job specified
    by JOB_ID to the file FILENAME. Print success/failure
    message.
    """
    client = connect()
    result = client.get_job_output(
        vaultName=VAULT_NAME,
        jobId=str(job_id))

    with open(filename) as f:
        f.write(result['Body'].read())
    print("File successfully downloaded.")

if __name__ == "__main__":
    arg1 = sys.argv[1]
    if (arg1 == "--start"):
        start_job(sys.argv[2])
    elif (arg1 == "--download"):
        download(sys.argv[2])
    elif (arg1 == "--delete"):
        delete_all(sys.argv[2])
    else:
        upload(sys.argv[1])

