import sys
import ssloop
import logging

logging.basicConfig(level=logging.DEBUG)

loop = ssloop.instance()


def on_connect(s):
    print 'on_connect'
    s.write('GET / HTTP/1.0\r\nHost: www.google.com\r\nConnection: Close\r\n\r\n')


def on_data(s, data):
    print 'on_data'
    sys.stdout.write(data)


def on_end(s):
    print 'on_end'


def on_close(s):
    print 'on_close'
    global loop
    loop.stop()


def on_error(s, e):
    print 'on_error'
    print e


s = ssloop.Socket()
s.on('connect', on_connect)
s.on('data', on_data)
s.on('end', on_end)
s.on('close', on_close)
s.on('error', on_error)
s.connect(('www.google.com', 80))

loop.start()
