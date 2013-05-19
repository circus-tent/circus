# sleeps for 55555 then leaks memory
import time

if __name__ == '__main__':
    time.sleep(5)
    memory = ''

    while True:
        memory += 100000 * ' '
