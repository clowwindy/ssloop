#!/usr/bin/python

import socket
import event
import loop as loop_
from loop import instance
import logging
import collections
import errno

STATE_CLOSED = 0
STATE_INITIALIZED = 1
STATE_CONNECTING = 2
STATE_STREAMING = 4
STATE_LISTENING = 8
STATE_CLOSING = 16  # half close, write only

RECV_BUFSIZE = 4096


class Socket(event.EventEmitter):
    ''' currently TCP, IPv4 only'''

    def __init__(self, loop=None, sock=None):
        super(Socket, self).__init__()
        self._loop = loop if loop is not None else instance()
        self._buffers = collections.deque()
        self._state = STATE_INITIALIZED
        self._connect_handler = None
        self._write_handler = None

        if sock is None:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self._socket.setblocking(False)
        else:
            # initialize using existing socket
            self._socket = sock
            sock.setblocking(False)
            self._init_streaming()

    def __del__(self):
        self.close()

    def end(self):
        assert self._state in (STATE_INITIALIZED, STATE_CONNECTING, STATE_STREAMING)
        if self._state in (STATE_INITIALIZED, STATE_CONNECTING):
            self.close()
        else:
            if self._buffers:
                logging.debug('wait for writing before closing')
                self._state = STATE_CLOSING
            else:
                self.close()

    def close(self):
        if self._state in (STATE_INITIALIZED, STATE_CONNECTING, STATE_STREAMING, STATE_CLOSING):
            # TODO remove handlers
            if self._state == STATE_CONNECTING:
                self._loop.remove_handler(self._connect_handler)
            elif self._state == STATE_STREAMING or self._state == STATE_CLOSING:
                if self._read_handler:
                    self._loop.remove_handler(self._read_handler)
                if self._write_handler:
                    self._loop.remove_handler(self._write_handler)

            self._socket.close()
            self._state = STATE_CLOSED
            self.emit('close', self)
        else:
            import traceback
            traceback.print_stack()
            logging.warn('closing a closed socket')

    def _error(self, error):
        self.emit('error', self, error)
        self.close()

    def _connect_cb(self):
        logging.debug('_connect_cb')
        assert self._state == STATE_CONNECTING
        self._loop.remove_handler(self._connect_handler)
        self._connect_handler = None
        self._init_streaming()
        self.emit('connect', self)

    def _init_streaming(self):
        logging.debug('init streaming')
        self._state = STATE_STREAMING
        self._read_handler = self._loop.add_fd(self._socket, loop_.MODE_IN, self._read_cb)

    def connect(self, address):
        logging.debug('connect')
        assert self._state == STATE_INITIALIZED
        try:
            self._socket.connect(address)
        except socket.error as e:
            if e.args[0] not in (errno.EINPROGRESS, errno.EWOULDBLOCK):
                self._error(e)
                return
        self._connect_handler = self._loop.add_fd(self._socket, loop_.MODE_OUT, self._connect_cb)
        self._state = STATE_CONNECTING

    def _read_cb(self):
        logging.debug('_read_cb')
        assert self._state == STATE_STREAMING
        self._read()

    def _read(self):
        logging.debug('_read')
        cache = []
        ended = False
        while True:
            try:
                data = self._socket.recv(RECV_BUFSIZE)
                if not data:
                    # received FIN
                    ended = True
                    break
                cache.append(data)
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    break
                else:
                    self._error(e)
                    return

        if cache:
            data = ''.join(cache)
            if data:
                self.emit('data', self, data)

        if ended:
            self.emit('end', self)
            if self._state == STATE_STREAMING:
                self.close()

    def _write_cb(self):
        logging.debug('_write_cb')
        assert self._state in (STATE_STREAMING, STATE_CLOSING)
        # called when writable
        if len(self._buffers) > 0:
            self._write()
        else:
            logging.debug('removing write handler %s' % self._write_handler)
            self._loop.remove_handler(self._write_handler)
            self._write_handler = None
            if self._state == STATE_CLOSING:
                self.close()

    def _write(self):
        logging.debug('_write')
        # called internally
        assert self._state in (STATE_STREAMING, STATE_CLOSING)
        buf = self._buffers
        while len(buf) > 0:
            data = buf.popleft()
            try:
                r = self._socket.send(data)
                if r < len(data):
                    buf.appendleft(data[r:])
                    logging.debug('r < data')
                    return
            except socket.error as e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    self._write_handler = self._loop.add_fd(self._socket, loop_.MODE_OUT, self._write_cb)
                    logging.debug(e)
                    return
                else:
                    self._error(e)
                    return
        # if all written, we don't need to handle OUT event
        logging.debug('removing write handler %s' % self._write_handler)
        self._loop.remove_handler(self._write_handler)
        self._write_handler = None
        if self._state == STATE_CLOSING:
            self.close()

    def write(self, data):
        # TODO make stream writable in STATE_CONNECTING
        self._buffers.append(data)
        if not self._write_handler:
            self._write_handler = self._loop.add_fd(self._socket, loop_.MODE_OUT, self._write_cb)
        self._write()


class Server(event.EventEmitter):
    ''' currently TCP, IPv4 only'''
    def __init__(self, address, loop=None):
        super(Server, self).__init__()
        self._address = address
        self._loop = loop if loop is not None else instance()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._socket.setblocking(False)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(address)
        self._state = STATE_INITIALIZED

    def __del__(self):
        self.close()

    def listen(self, backlog=128):
        assert self._state == STATE_INITIALIZED
        self._accept_handler = self._loop.add_fd(self._socket, loop_.MODE_IN, self._accept_cb)
        self._socket.listen(backlog)
        self._state = STATE_LISTENING

    def _accept_cb(self):
        assert self._state == STATE_LISTENING
        logging.debug('accept_cb')
        conn, addr = self._socket.accept()
        sockobj = Socket(loop=self._loop, sock=conn)
        self.emit('connection', self, sockobj)

    def close(self):
        logging.debug('close server')
        if self._state in (STATE_INITIALIZED, STATE_LISTENING):
            if self._accept_handler:
                self._loop.remove_handler(self._accept_handler)
            self._socket.close()
            self._state = STATE_CLOSED
            self.emit('close', self)
        else:
            logging.warn('closing a closed server')
