import sys
import ssloop
import logging

logging.basicConfig(level=logging.DEBUG)

loop = ssloop.instance()


def on_connect(s):
    print 'on_connect'
    s.write('GET /\r\nHost: www.baidu.com\r\n\r\n')


def on_data(s, data):
    print 'on_data'
    sys.stdout.write(data)


def on_close(s):
    print 'on_close'


def on_error(s, e):
    print 'on_error'
    print e


s = ssloop.Socket()
s.on('connect', on_connect)
s.on('data', on_data)
s.on('close', on_close)
s.on('error', on_error)
s.connect(('www.baidu.com', 80))

loop.start()
