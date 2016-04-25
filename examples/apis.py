
from circus import get_arbiter

myprogram = {"cmd": "sleep 30", "numprocesses": 4}

print('Runnning...')
arbiter = get_arbiter([myprogram])
try:
    arbiter.start()
finally:
    arbiter.stop()
