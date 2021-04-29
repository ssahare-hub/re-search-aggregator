import logging
import uuid
import os
from flask import Flask, request
from threading import Thread
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
import json
import sys
from worker import *
import base64
# from google.cloud.pubsub_v1.types import FlowControl


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
    dl = blob.download_as_string()
    # blob.download_to_filename(destination_file_name)

    print(
        "Blob was downloaded to \n {}.".format(
            dl
        )
    )
    return dl


SECRET_KEY = "VERYCONFIDENTIAL"
UPLOAD_FOLDER = "/uploads/"
# CHANGE THESE VALUES ACCORDING TO YOUR APP ENGINE ACCOUNT
BUCKET_NAME = os.environ.get(
    "BUCKET_NAME", "staging.sss-cc-gae-310003.appspot.com")
PROJECT_ID = os.environ.get("PROJECT_ID", "sss-cc-gae-310003")

# host flask server
app = Flask(__name__)

# TODO: Create all topics and subscription if they
# don't exists

# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
c = download_blob(BUCKET_NAME, 'constants.json')
constants = json.loads(c)

pub_client = PublisherClient()
sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(
    PROJECT_ID, constants["job-worker-sub"])
top_path = pub_client.topic_path(PROJECT_ID, constants["output-topic"])

# POST endpoint at '/job/'


@app.route('/job/', methods=['POST'])
def process_job():
    envelope = json.loads(request.data.decode('utf-8'))
    data_str = base64.b64decode(envelope['message']['data'])
    data = json.loads(data_str)
    message = data["URL"]
    
    # TEST PURPOSES ONLY
    value = redis_client.incr('{}_messages_received'.format(data["JobId"]))
    eid = '2'
    key = ds_client.key('Messages', eid)
    entity = Entity(key=key, exclude_from_indexes=('description',))
    entity['description'] = "message_receieved"
    entity['value'] = value
    ds_client.put(entity)

    # to prevent processing of same links
    job_id = data["JobId"]

    # lists all memebrs of the set with name 'job_id'
    members = redis_client.smembers(job_id)

    # if empty
    if len(members) == 0:
        redis_client.sadd(job_id, message)
    # if not empty
    else:
        # if message is a member of job_id
        # we acknowledge the message and skip processing
        if redis_client.sismember(job_id, message):
            # pay_load.ack()
            value = redis_client.incr('{}_messages_skipped'.format(data["JobId"]))
            # TEST PURPOSES ONLY
            eid = '4'
            key = ds_client.key('Messages',eid)
            entity = Entity(key=key, exclude_from_indexes=('description',))
            entity['description'] = "messages_skipped"
            entity['value'] = value
            ds_client.put(entity)
            return 'OK', 200
        # else add to set and process
        else:
            redis_client.sadd(job_id, message)

    prof_obs = []
    links = []
    threads = []
    if data["Type"] == constants["faculty"]:
        parse_faculty_page(message, data)
    elif data["Type"] == constants["profile"]:
        extract_links_isearch(message, data)
    elif data["Type"] == constants["pdf"]:
        parse_pdf(message, data)
    else:
        extract_links_others(message, data)
    # pay_load.ack()
    return 'OK', 200

# socket io listeners and event emitters start here


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    logging.exception('Error was ----> \n{}\n'.format(e))
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


# TODO: listen to response subscription
# listening to subscription for output topic
if __name__ == '__main__':
    # print('starting listening to output sub')
    # t1 = Thread(target=output_listener_thread)
    # t1.start()
    print('starting listening to server events')
    # socketio.run(
    #     app, host='0.0.0.0', port=os.environ.get('PORT', 8080)
    # )
