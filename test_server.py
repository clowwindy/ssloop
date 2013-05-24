import sys
import ssloop
import logging

logging.basicConfig(level=logging.DEBUG)

loop = ssloop.instance()


def on_connection(s, conn):
    print 'on_connection'
    conn.on('data', on_data)
    conn.on('end', on_end)
    conn.on('close', on_close)
    conn.on('error', on_error)


def on_data(s, data):
    print 'on_data'
    sys.stdout.write(data)
    s.write('HTTP/1.0 200 OK\r\nHost: www.google.com\r\nConnection: Close\r\n\r\nHello world!\r\n')
    s.end()


def on_end(s):
    print 'on_end'


def on_close(s):
    print 'on_close'


def on_error(s, e):
    print 'on_error'
    print e


s = ssloop.Server(('0.0.0.0', 8080))
s.on('connection', on_connection)
s.on('error', on_error)
s.listen()

loop.start()
