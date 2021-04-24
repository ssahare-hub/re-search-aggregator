from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
import sys
from google.cloud.pubsub_v1.types import FlowControl
import json
from google.cloud import storage
import uuid
import os
import threading
import time
from worker import parse_faculty_page, extract_links_isearch, extract_links_others, parse_pdf
import redis
import getopt


def download_blob(bucket_name, source_blob_name):
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
    # blob.download_to_filename(destination_file_name)
    dl = blob.download_as_string()
    print("download blob", dl)
    return dl
# CHANGE THESE VALUES ACCORDING TO YOUR APP ENGINE ACCOUNT
# Or pass an environment variable thorught the start__ script
BUCKET_NAME = os.environ.get(
    "BUCKET_NAME", "cc-test-309723.appspot.com")
PROJECT_ID = os.environ.get("PROJECT_ID", "cc-test-309723")
request_count = 0
1
# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
download_blob(BUCKET_NAME, 'constants.json')
constants = json.loads(c)

pub_client = PublisherClient()
top_path = pub_client.topic_path(PROJECT_ID, constants["output-topic"])


sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(
    PROJECT_ID, constants["job-worker-sub"])
flow_control = FlowControl(max_messages=50)


redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = os.environ.get('REDIS_PORT', '6379')
redis_client = redis.Redis(host=redis_host, port=redis_port)
redis_client.set('messages_received', 0)


# argv = sys.argv[1]
# try:
#     opts, args = getopt.getopt(argv,"d:",["delete="])
# except getopt.GetoptError:
#     print("Redis will not be flushed")
# for opt, arg in opts:
#     if opt == '-d':
#         print("Flushing redis ", opt)
#         redis_client.flushall()


def process_job(pay_load):
    data_str = pay_load.data.decode("UTF-8")
    data = json.loads(data_str)
    message = data["URL"]
    redis_client.incr('messages_received')
    # to prevent processing of same links
    if redis_client.get(message):
        print('already parsed', message)
        pay_load.ack()
        return
    else:
        redis_client.set(message, 'Parsed')

    prof_obs = []
    links = []
    threads = []
    if data["Type"] == constants["faculty"]:
        parse_faculty_page(message, data["Level"], data["Meta"])
    elif data["Type"] == constants["profile"]:
        extract_links_isearch(message, data["Level"], data["Meta"])
    elif data["Type"] == constants["pdf"]:
        parse_pdf(message, data["Meta"])
    else:
        extract_links_others(message, data["Level"], data["Meta"])
    pay_load.ack()


# Removed flow control for testing
print('listening to {} path for messages'.format(sub_path))
sub_future = sub_client.subscribe(
    sub_path, callback=process_job)

try:
    sub_future.result()
except:
    print('some error while subscribing to {}'.format(sub_path))
    sub_future.cancel()
