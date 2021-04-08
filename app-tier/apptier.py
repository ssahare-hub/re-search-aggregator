from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
import json
from google.cloud import storage
import uuid
import os
import time
from worker import work_on_jobs


def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

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


BUCKET_NAME = "staging.sss-cc-gae-310003.appspot.com"
PROJECT_ID = "sss-cc-gae-310003"

download_blob(BUCKET_NAME, 'constants.json', 'constants.json')
with open('constants.json','r') as c:
    constants = json.load(c)

pub_client = PublisherClient()
sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(PROJECT_ID, constants["job-worker-sub"])
top_path = pub_client.topic_path(PROJECT_ID, constants["output-topic"])


def process_job(pay_load):
    message = pay_load.data.decode("UTF-8")
    prof_obs, links = work_on_jobs(message)
    print('sending messageS {}'.format(len(prof_obs)))
    for prof in prof_obs:
        prof['total'] = len(prof_obs)
        data = json.dumps(prof).encode("UTF-8")
        future = pub_client.publish(top_path, data)
        try:
            message_id = future.result()
        except:
            print("Some error while sending message to {}".format(top_path))
    pay_load.ack()

print('listening to {} path for messages'.format(sub_path))
sub_future = sub_client.subscribe(sub_path, callback = process_job)

try:
    sub_future.result()
except:
    print('some error while subscribing to {}'.format(sub_path))
    sub_future.cancel()


