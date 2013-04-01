#!/usr/bin/python

import select

from ssloop.loop import SSLoop


class EpollLoop(SSLoop):

    def __init__(self):
        super(EpollLoop, self).__init__()
        self._epoll = select.epoll()

    def _poll(self, timeout):
        return self._epoll.poll(timeout)

    def _add_fd(self, fd, mode):
        self._epoll.register(fd, mode)

    def _remove_fd(self, fd):
        self._epoll.unregister(fd)

    def _modify_fd(self, fd, mode):
        self._epoll.modify(fd, mode)
