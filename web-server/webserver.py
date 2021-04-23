import uuid
import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO
from threading import Thread
from google.cloud import storage
from google.cloud.pubsub_v1 import PublisherClient, SubscriberClient
import json
# from google.cloud.pubsub_v1.types import FlowControl

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


SECRET_KEY = "VERYCONFIDENTIAL"
UPLOAD_FOLDER = "/uploads/"
# CHANGE THESE VALUES ACCORDING TO YOUR APP ENGINE ACCOUNT

BUCKET_NAME = os.environ.get(
    "BUCKET_NAME", "staging.sss-cc-gae-310003.appspot.com")
PROJECT_ID = os.environ.get("PROJECT_ID", "sss-cc-gae-310003")

# host flask server
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
is_get = False

# create socket connection
socketio = SocketIO(app)
# allow requests from cross origin domains
socketio.init_app(app, cors_allowed_origins="*")

# TODO: Create all topics and subscription if they 
# don't exists

# UPLOAD THIS FILE ONTO YOUR CLOUD STORAGE
download_blob(BUCKET_NAME, 'constants.json', 'constants.json')
with open('constants.json','r') as c:
    constants = json.load(c)

pub_client = PublisherClient()
sub_client = SubscriberClient()
sub_path = sub_client.subscription_path(PROJECT_ID, constants["result-sub"])
top_path = pub_client.topic_path(PROJECT_ID, constants["job-topic"])

# GET & POST endpoint at '/'
@app.route('/', methods=['GET', 'POST'])
def home_page():
    is_get = (request.method == 'GET')
    job_id = ""
    if not is_get:
        job_id = "INVALID_DATA"
        # job_id = str(uuid.uuid4())
        # TODO: fetch data from requests
        # website = request.args.get('website')
        website = request.form.get('text')
        # request_data = request.get_json()
        print('received data from POST', website)
        if website:
            data_obj = {
                "URL" : website,
                "Type" : constants["faculty"],
                "Level" : 0,
                "Meta": ""
            }
            data_str = json.dumps(data_obj)
            data = data_str.encode("UTF-8")
            # TODO: post message in topic
            try:
                future = pub_client.publish(top_path, data)
                job_id = future.result()
            except:
                job_id = "CANNOT_PUBLISH_TO_TOPIC"
        
    # get / render front end page
    return render_template(
        'index.html'
        , is_get = is_get
        , job_id = job_id
    )

# socket io listeners and event emitters start here
@socketio.on('connect')
def connected():
    print('connected')
    socketio.emit('on_connect', is_get)


@socketio.on('disconnect')
def disconnected():
    print('disconnected')


def output_listener_thread():
    def output_callback(data):
        msg = data.data.decode("UTF-8")
        print('emitting result ', msg)
        socketio.emit("partial_result", msg)
        data.ack()
    future = sub_client.subscribe(sub_path, callback = output_callback)
    try:
        future.result(timeout=None)
    except:
        future.cancel()


# TODO: listen to response subscription
# listening to subscription for output topic
if __name__ == '__main__':
    print('starting listening to output sub')
    t1 = Thread(target=output_listener_thread)
    t1.start()
    print('starting listening to server events')
    socketio.run(
        app         
        , host='0.0.0.0'
        , port=8080
    )
