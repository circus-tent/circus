# -*- coding: utf-8 -*-
"""
    Bread: A Simple Web Client for Circus

"""
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

import json
import argparse

from circus.consumer import CircusConsumer
from flask import Flask, request, render_template


ZMQ_ENDPOINT = 'tcp://127.0.0.1:5556'

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api')
def api():
    """WebSocket endpoint; Takes a 'topic' GET param."""
    ws = request.environ.get('wsgi.websocket')
    topic = request.args.get('topic')

    if None in (ws, topic):
        return

    topic = topic.encode('ascii')
    for message, message_topic in CircusConsumer(topic, endpoint=ZMQ_ENDPOINT):
        response = json.dumps(dict(message=message, topic=message_topic))
        ws.send(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=5000)
    args = parser.parse_args()
    server_loc = (args.host, args.port)
    print('HTTP Server running at http://%s:%s/...' % server_loc)
    http_server = WSGIServer(server_loc, app, handler_class=WebSocketHandler)
    http_server.serve_forever()


if __name__ == '__main__':
    main()
