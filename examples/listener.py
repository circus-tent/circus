from circus.consumer import CircusConsumer
import json


ZMQ_ENDPOINT = 'tcp://127.0.0.1:5556'
topic = 'show:'

for message, message_topic in CircusConsumer(topic, endpoint=ZMQ_ENDPOINT):
    response = json.dumps(dict(message=message, topic=message_topic))
    print(response)
