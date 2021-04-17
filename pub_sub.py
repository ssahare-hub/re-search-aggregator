import argparse
import os
credential_path = r'C:\Users\ssomarou\Downloads\cc-test-309723-048a23801f92.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path


from google.cloud import pubsub_v1
import json
import os

with open('test.json', 'r') as c:
    test = json.load(c)
print (test)

def createtopic():
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path('cc-test-309723', 'sai_output_topic')
    topic = publisher.create_topic(request={"name": topic_path})
    print("Created topic: {}".format(topic.name))


'''publisher = pubsub_v1.PublisherClient()
topic_name = 'projects/{project_id}/topics/{topic}'.format(
    project_id = 'cc-test-309723',
    topic='sai_output_topic',  # Set this to something appropriate.
)
publisher.create_topic(topic_name)'''

def createsubscription():
    publisher = pubsub_v1.PublisherClient()
    subscriber = pubsub_v1.SubscriberClient()
    topic_path = publisher.topic_path('cc-test-309723', 'sai_output_topic')
    subscription_path = subscriber.subscription_path('cc-test-309723', 'test_Subscription')

# Wrap the subscriber in a 'with' block to automatically call close() to
# close the underlying gRPC channel when done.
    with subscriber:
        subscription = subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path}
    )

    print(f"Subscription created: {subscription}")




def pub(project_id, topic_id):
    """Publishes a message to a Pub/Sub topic."""
    # Initialize a Publisher client.
    client = pubsub_v1.PublisherClient()
    # Create a fully qualified identifier of form `projects/{project_id}/topics/{topic_id}`
    topic_path = client.topic_path(project_id, topic_id)

    # Data sent to Cloud Pub/Sub must be a bytestring.
    for i in range(12):
        data = b"Hello, World!{}"

    # When you publish a message, the client returns a future.
        api_future = client.publish(topic_path, data)
        message_id = api_future.result()

        print(f"Published {data} to {topic_path}: {message_id}")


pub('cc-test-309723', 'sai_output_topic')

def listenresults():
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path('cc-test-309723', 'test_Subscription')

    def callback(message):
        print(f"Received {message.data}.")
        message.ack()

# Limit the subscriber to only have ten outstanding messages at a time.
    flow_control = pubsub_v1.types.FlowControl(max_messages=10)

    streaming_pull_future = subscriber.subscribe(
        subscription_path, callback=callback, flow_control=flow_control
    )
    print(f"Listening for messages on {subscription_path}..\n")
    timeout = 20.0
# Wrap subscriber in a 'with' block to automatically call close() when done.
    with subscriber:
        try:
        # When `timeout` is not set, result() will block indefinitely,
        # unless an exception is encountered first.
            streaming_pull_future.result(timeout=timeout)
        except TimeoutError:
            streaming_pull_future.cancel()

from google.cloud import datastore

# Instantiates a client
datastore_client = datastore.Client()

# The kind for the new entity
kind = "Task"
# The name/ID for the new entity
name = "sampletask1"
# The Cloud Datastore key for the new entity
task_key = datastore_client.key(kind, name)

# Prepares the new entity
task = datastore.Entity(key=task_key)
task["description"] = "Buy milk"

# Saves the entity
datastore_client.put(task)

print(f"Saved {task.key.name}: {task['description']}")