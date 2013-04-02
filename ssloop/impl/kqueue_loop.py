#!/usr/bin/python

import select
import ssloop.loop as loop
from ssloop.loop import SSLoop
from collections import defaultdict

MAX_EVENTS = 1024


class KqueueLoop(SSLoop):

    def __init__(self):
        super(KqueueLoop, self).__init__()
        self._kqueue = select.kqueue()
        self._fds = {}

    def _control(self, fd, mode, flags):
        events = []
        if mode & loop.MODE_IN:
            events.append(select.kevent(fd, select.KQ_FILTER_READ, flags))
        if mode & loop.MODE_OUT:
            events.append(select.kevent(fd, select.KQ_FILTER_WRITE, flags))
        for e in events:
            self._kqueue.control([e], 0)

    def _poll(self, timeout):
        if timeout < 0:
            timeout = None  # kqueue behaviour
        events = self._kqueue.control(None, MAX_EVENTS, timeout)
        results = defaultdict(lambda: loop.MODE_NULL)
        for e in events:
            fd = e.ident
            if e.filter == select.KQ_FILTER_READ:
                results[fd] |= loop.MODE_IN
            elif e.filter == select.KQ_FILTER_WRITE:
                results[fd] |= loop.MODE_OUT
        return results.iteritems()

    def _add_fd(self, fd, mode):
        self._fds[fd] = mode
        self._control(fd, mode, select.KQ_EV_ADD)

    def _remove_fd(self, fd):
        self._control(fd, self._fds[fd], select.KQ_EV_DELETE)
        del self._fds[fd]

    def _modify_fd(self, fd, mode):
        self._remove_fd(fd)
        self._add_fd(fd, mode)
