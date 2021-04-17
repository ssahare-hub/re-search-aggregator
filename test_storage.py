# Imports the Google Cloud client library
import os
credential_path = r'C:\Users\ssomarou\Downloads\cc-test-309723-048a23801f92.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
from google.cloud import storage
# Instantiates a client
def create_bucket():
    storage_client = storage.Client()

# The name for the new bucket
    bucket_name = "cc-sai-bucket"

# Creates the new bucket
    bucket = storage_client.create_bucket(bucket_name)

    print("Bucket {} created.".format(bucket.name))


def upload_blob():
    """Uploads a file to the bucket."""
    bucket_name = "sai-bucket"
    source_file_name = r"C:\Users\ssomarou\Desktop\GAP_CC\re-search-aggregator\app-tier\constants.json"
    destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )
upload_blob()

def download_blob():
    """Downloads a blob from the bucket."""
    bucket_name = "sai-bucket"
    source_blob_name = "storage-object-name"
    destination_file_name = "test"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    # Construct a client side representation of a blob.
    # Note `Bucket.blob` differs from `Bucket.get_blob` as it doesn't retrieve
    # any content from Google Cloud Storage. As we don't need additional data,
    # using `Bucket.blob` is preferred here.
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    print(
        "Blob {} downloaded to {}.".format(
            source_blob_name, destination_file_name
        )
    )

download_blob()