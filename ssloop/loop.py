#!/usr/bin/python

import select
import time
import heapq
import logging
from collections import defaultdict
import sys
import traceback


''' You can only use instance(). Don't create a Loop() '''

_ssloop_cls = None
_ssloop = None


def instance():
    global _ssloop
    if _ssloop is not None:
        return _ssloop
    else:
        init()
        _ssloop = _ssloop_cls()
        return _ssloop


def init():
    global _ssloop_cls

    if 'epoll' in select.__dict__:
        import impl.epoll_loop
        logging.debug('using epoll')
        _ssloop_cls = impl.epoll_loop.EpollLoop
    elif 'kqueue' in select.__dict__:
        import impl.kqueue_loop
        logging.debug('using kqueue')
        _ssloop_cls = impl.kqueue_loop.KqueueLoop
    else:
        import impl.select_loop
        logging.debug('using select')
        _ssloop_cls = impl.select_loop.SelectLoop


# these values are defined as the same as poll
MODE_NULL = 0x00
MODE_IN = 0x01
MODE_OUT = 0x04
MODE_ERR = 0x08
MODE_HUP = 0x10
MODE_NVAL = 0x20


class Handler(object):
    def __init__(self, callback, fd=None, mode=None, deadline=None, error=None):
        '''deadline here is absolute timestamp'''
        self.callback = callback
        self.fd = fd
        self.mode = mode
        self.deadline = 0
        self.error = None  # a message describing the error

    def __cmp__(self, other):
        r = self.deadline - other.deadline
        if r != 0:
            return r
        else:
            # We don't want to make lists think 2 handlers are equal
            return id(self) - id(other)


class SSLoop(object):

    def __init__(self):
        self._handlers_with_no_fd = []
        # [handle1, handle2, ...]

        self._handlers_with_timeout = []
        # [handle1, handle2, ...]

        self._stopped = False

        self._fd_to_handler = defaultdict(list)
        # {'fd1':[handler, handler, ...], 'fd2':[handler, handler, ...]}

        self._on_error = None

    def time(self):
        return time.time()

    def _poll(self, timeout):
        '''timeout here is timespan, -1 means forever'''
        raise NotImplementedError()

    def _add_fd(self, fd, mode):
        raise NotImplementedError()

    def _remove_fd(self, fd):
        raise NotImplementedError()

    def _modify_fd(self, fd, mode):
        raise NotImplementedError()

    def _call_handler(self, handler):
        try:
            handler.callback()
        except:
            if self._on_error is not None:
                self._on_error(sys.exc_info())
            else:
                traceback.print_exc()

    def _get_fd_mode(self, fd):
        mode = MODE_NULL
        handlers = self._fd_to_handler[fd]
        if handlers is None:
            return None
        for handler in handlers:
            mode |= handler.mode
        return mode

    def _update_fd(self, fd):
        mode = self._get_fd_mode(fd)
        if mode is not None:
            self._modify_fd(fd, mode)

    def start(self):
        self._stopped = False
        while not self._stopped:
            # TODO make a copy of these handlers before iterating on them

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
            else:
                timeout = -1

            # poll handlers with fd
            fds_ready = self._poll(timeout)
            for fd, mode in fds_ready:
                handlers = self._fd_to_handler[fd]
                for handler in handlers:
                    if handler.mode & mode != 0:
                        logging.debug('calling %s' % handler)
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
        if not isinstance(fd, int):
            fd = fd.fileno()
        handler = Handler(callback, fd=fd, mode=mode)
        l = self._fd_to_handler[fd]
        l.append(handler)
        if len(l) == 1:
            self._add_fd(fd, mode)
        else:
            self._update_fd(fd)
        return handler

    def update_handler_mode(self, handler, mode):
        handler.mode = mode
        self._update_fd(handler.fd)

    def remove_handler(self, handler):
        # TODO: handle exceptions friendly
        if handler.deadline:
            self._handlers_with_timeout.remove(handler)
        elif handler.fd:
            fd = handler.fd
            if not isinstance(fd, int):
                fd = fd.fileno()
            l = self._fd_to_handler[fd]
            # TODO: handle exceptions friendly
            l.remove(handler)
            if len(l) == 0:
                self._remove_fd(fd)
                del self._fd_to_handler[fd]
            else:
                self._update_fd(fd)
        else:
            self._handlers_with_no_fd.remove(handler)
