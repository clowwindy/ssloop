#!/usr/bin/python

import socket
import event
import loop
import logging
import collections
import errno

STATE_CLOSED = 0
STATE_INITIALIZED = 1
STATE_CONNECTING = 2
STATE_STREAMING = 4


class Socket(event.EventEmitter):
    ''' currently TCP, IPv4 only'''

    def __init__(self, loop):
        super(Socket).__init__()
        self._loop = loop
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._socket.setblocking(False)
        self._buffers = collections.deque()
        self._state = STATE_INITIALIZED
        self._connect_handler = None
        self._write_handler = None

    def __del__(self):
        self.close()

    def close(self):
        if self._state in (STATE_INITIALIZED, STATE_CONNECTING, STATE_STREAMING):
            # TODO remove handlers
            if self._stage == STATE_CONNECTING:
                self._loop.remove(self._connect_cb)

            self._socket.close()
            self._state = STATE_CLOSED
        else:
            logging.warn('closing a closed socket')

    def _connect_cb(self):
        assert self._state == STATE_CONNECTING
        self.emit('connect', self)
        self._loop.remove_handler(self._connect_handler)
        self._connect_handler = None
        self._state == STATE_STREAMING

    def connect(self, address):
        assert self._state == STATE_INITIALIZED
        self._socket.connect(address)
        self._connect_handler = self._loop.add(self._socket, loop.MODE_OUT, self._connect_cb)

    def _write_cb(self):
        # called when writable
        if len(self._buffers) > 0:
            self._write()
        else:
            self._loop.remove_handler(self._write_handler)
            self._write_handler = None

    def _write(self):
        # called internally
        assert self._state == STATE_STREAMING
        buf = self._buffers
        while len(buf) > 0:
            data = buf.popleft()
            try:
                r = socket.send(data)
                if r < len(data):
                    buf.appendleft(data[r:])
                    return
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
        # if all written, we don't need to handle OUT event
        self._loop.remove_handler(self._write_handler)
        self._write_handler = None

    def write(self, data):
        # TODO make stream writable in STATE_CONNECTING
        self._buffers.append(data)
        if not self._write_handler:
            self._write_handler = self._loop.add(self._socket, loop.MODE_OUT, self._write_cb)
        self._write()




