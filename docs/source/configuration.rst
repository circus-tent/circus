Configuration
-------------

Circus can be configured to run with a ini-style file. 

Example::

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:5555

    [show:myprogram]
    cmd = python
    args = -u myprogram.py $WID
    warmup_delay = 0
    num_flies = 5


XXX put all options here
