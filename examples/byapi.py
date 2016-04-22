from circus import get_arbiter


myprogram = {
    "cmd": "python",
    "args": "-u dummy_fly.py $(circus.wid)",
    "numprocesses": 3,
}


arbiter = get_arbiter([myprogram], debug=True)
try:
    arbiter.start()
finally:
    arbiter.stop()
