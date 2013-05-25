import sys
import ssloop
import logging

logging.basicConfig(level=logging.DEBUG)

loop = ssloop.instance()


def on_connect(s):
    print 'on_connect'
    s.write('POST / HTTP/1.0\r\nHost: www.google.com\r\nContent-Length: 1000000\r\nConnection: Close\r\n' + ' ' * 1000000)
    # this is an invalid request


def on_data(s, data):
    print 'on_data'
    sys.stdout.write(data)


def on_end(s):
    print 'on_end'


def on_close(s):
    print 'on_close'
    global loop
    loop.stop()


def on_drain(s):
    print 'on_drain'


def on_error(s, e):
    print 'on_error'
    print e


s = ssloop.Socket()
s.on('connect', on_connect)
s.on('data', on_data)
s.on('drain', on_drain)
s.on('end', on_end)
s.on('close', on_close)
s.on('error', on_error)
s.connect(('www.google.com', 80))

loop.start()
