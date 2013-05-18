# sleeps for 55555 then leaks memory
import time

time.sleep(5)
memory = ''

while True:
    memory += 100000 * ' '
