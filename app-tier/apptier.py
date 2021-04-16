from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
from google.cloud.pubsub_v1.types import FlowControl
import json
from google.cloud import storage
import uuid
import os
import threading
import time
from worker import work_on_jobs, extract_links_isearch, extract_links_others, parse_pdf


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


BUCKET_NAME = "cc-test-309723.appspot.com"
PROJECT_ID = "cc-test-309723"
request_count = 0

download_blob(BUCKET_NAME, 'constants.json', 'constants.json')
with open('constants.json', 'r') as c:
    constants = json.load(c)

pub_client = PublisherClient()
top_path = pub_client.topic_path(PROJECT_ID, constants["output-topic"])


sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(
    PROJECT_ID, constants["job-worker-sub"])
flow_control = FlowControl(max_messages=50)


def process_job(pay_load):
    data_str = pay_load.data.decode("UTF-8")
    data = json.loads(data_str)
    message = data["URL"]
    prof_obs = []
    links = []
    threads = []
    if data["Type"] == constants["faculty"]:
        # thread = threading.Thread(
        #     target=work_on_jobs, args=(message, data["Level"],))
        # threads.append(thread)
        # thread.start()
        work_on_jobs(message, data["Level"], data["Meta"])
    elif data["Type"] == constants["profile"]:
        # thread = threading.Thread(
        #     target=extract_links_isearch, args=(message, data["Level"],))
        # threads.append(thread)
        # thread.start()
        extract_links_isearch(message, data["Level"], data["Meta"])
    elif data["Type"] == constants["pdf"]:
    #     thread = threading.Thread(target=parse_pdf, args=(message,))
    #     threads.append(thread)
    #     thread.start()
        parse_pdf(message, data["Meta"])
    else:
        extract_links_others(message, data["Level"], data["Meta"])
        # thread = threading.Thread(
        #     target=extract_links_others, args=(message, data["Level"],))
        # threads.append(thread)
        # thread.start()
    # for thread in threads:
    #     thread.join()
    pay_load.ack()


print('listening to {} path for messages'.format(sub_path))
sub_future = sub_client.subscribe(
    sub_path, callback=process_job, flow_control=flow_control)

try:
    sub_future.result()
except:
    print('some error while subscribing to {}'.format(sub_path))
    sub_future.cancel()
