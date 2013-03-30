#!/usr/bin/python

import select

from collections import defaultdict
from ssloop.loop import SSLoop


class SelectLoop(SSLoop):

    def __init__(self):
        super(SelectLoop).__init__(self)
        self._r_list = set()
        self._w_list = set()
        self._x_list = set()

    def _poll(self, timeout):
        r, w, x = select.select(self._r_list, self._w_list, self._x_list)
        results = defaultdict(lambda: SSLoop.NULL)
        for p in [(r, SSLoop.MODE_IN), (w, SSLoop.MODE_OUT), (x, SSLoop.MODE_ERR)]:
            for fd in p[0]:
                results[fd] &= p[1]
        return results

    def _add_fd(self, fd, mode):
        if mode & SSLoop.MODE_IN:
            self._r_list.add(fd)
        if mode & SSLoop.MODE_OUT:
            self._w_list.add(fd)
        if mode & SSLoop.MODE_ERR:
            self._x_list.add(fd)

    def _remove_fd(self, fd):
        if fd in self._r_list:
            self._r_list.remove(fd)
        if fd in self._w_list:
            self._w_list.remove(fd)
        if fd in self._x_list:
            self._x_list.remove(fd)

    def _modify_fd(self, fd, mode):
        self._remove_fd(fd)
        self._add_fd(fd, mode)
