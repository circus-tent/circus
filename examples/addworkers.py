from circus.client import CircusClient
from circus.util import DEFAULT_ENDPOINT_DEALER

client = CircusClient(endpoint=DEFAULT_ENDPOINT_DEALER)

command = '../bin/python dummy_fly.py 111'
name = 'dummy'


for i in range(50):
    print(client.call("""
    {
        "command": "add",
        "properties": {
            "cmd": "%s",
            "name": "%s",
            "options": {
            "copy_env": true,
            "stdout_stream": {
                "filename": "stdout.log"
            },
            "stderr_stream": {
                "filename": "stderr.log"
            }
            },
            "start": true
        }
    }
    """ % (command, name + str(i))))
