#!/usr/bin/env python
import os
import time
import sys

i = 0

while True:
    # print '%d:%d' % (os.getpid(), i)
    sys.stdout.write('%d:%d\n' % (os.getpid(), i))
    sys.stdout.flush()
    time.sleep(0.1)
    i += 1
