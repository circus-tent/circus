myprogram = {
    "cmd": "python",
    "args": "-u dummy_fly.py $(circus.wid)",
    "numprocesses": 3,
}

from circus import get_arbiter

arbiter = get_arbiter([myprogram], debug=True)
try:
    arbiter.start()
finally:
    arbiter.stop()

