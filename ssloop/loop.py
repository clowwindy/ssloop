#!/usr/bin/python

import select
import time
import heapq
import sys

_ssloop_cls = None
_ssloop = None


def instance():
    global _ssloop
    if _ssloop is not None:
        return _ssloop
    else:
        _ssloop = _ssloop_cls()
        return _ssloop


def init():
    global _ssloop_cls

    if 'epoll' in select.__all__:
        import impl.epoll_loop
        _ssloop_cls = impl.epoll_loop.EpollLoop
    elif 'kqueue' in select._all__:
        import impl.kqueue_loop
        _ssloop_cls = impl.kqueue_loop.KqueueLoop
    else:
        import impl.select_loop
        _ssloop_cls = impl.select_loop.SelectLoop

init()

MODE_NULL = 0
MODE_IN = 1
MODE_OUT = 2
MODE_ERR = 4
MODE_HUP = 8
MODE_NVAL = 16


class Handler(object):
    def __init__(self, callback, fd=None, mode=None, deadline=None, error=None):
        '''deadline here is absolute timestamp'''
        self.callback = callback
        self.fd = fd
        self.mode = mode
        self.deadline = 0
        self.error = None  # a message describing the error

    def __cmp__(self, other):
        return self.deadline - other.deadline


class SSLoop(object):

    def __init__(self):
        self._handlers_with_no_fd = []
        # [handle1, handle2, ...]

        self._handlers_with_fd = []
        # [handle1, handle2, ...]

        self._handlers_with_timeout = []
        # [handle1, handle2, ...]

        self._stopped = False
        self._fd_to_handler = {}
        self._on_error = None

    def time(self):
        return time.time()

    def _poll(self, timeout):
        '''timeout here is timespan, -1 means forever'''
        raise NotImplementedError()

    def _call_handler(self, handler):
        try:
            handler.callback()
        except:
            if self._on_error is not None:
                self._on_error(sys.exc_info())
            else:
                sys.print_exc()

    def start(self):
        self._stopped = False
        while not self._stopped:
            # call handlers timed out
            # notice that handlers with timeout are called first than handlers without fd
            cur_time = self.time()
            while len(self._handlers_with_timeout) > 0:
                handler = heapq.heappop(self._handlers_with_no_fd)
                if handler.deadline <= cur_time:
                    self._handlers_with_timeout.remove(handler)
                    self._call_handler(handler)
                else:
                    # because the queue is sorted
                    break

            # call handlers without fd
            for handler in self._handlers_with_no_fd:
                self._call_handler(handler)
            self._handlers_with_no_fd = []

            cur_time = self.time()
            if len(self._handlers_with_timeout) > 0:
                next_deadline = self._handlers_with_timeout[0].deadline
            timeout = next_deadline - cur_time
            if timeout < 0:
                timeout = 0

            # poll handlers with fd
            handlers_ready = self._poll(0)
            for handler in handlers_ready:
                self._call_handler(handler)

    def stop(self):
        self._stopped = True

    def add_callback(self, callback):
        handler = Handler(callback)
        self._handlers_with_no_fd.append(handler)
        return handler

    def add_timeout(self, timeout, callback):
        handler = Handler(callback, deadline=self.time() + timeout)
        # sort timeouts in order
        heapq.heappush(self._handlers_with_timeout, handler)
        return handler

    def add_fd(self, fd, mode, callback):
        handler = Handler(callback, fd=fd, mode=mode)
        self._handers_with_fd.append(handler)
        return handler

    def remove_handler(self, handler):
        if handler.timeout:
            self._handlers_with_timeout.remove(handler)
        elif handler.fd:
            self._handlers_with_fd.remove(handler)
        else:
            self._handlers_with_no_fd.remove(handler)
