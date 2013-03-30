#!/usr/bin/python

import select


class SelectLoop(object):

    def __init__(self):
        super(SelectLoop).__init__(self)
        self._r_list = []
        self._w_list = []
        self._x_list = []

    def _poll(self, timeout):
        r, w, x = select.select(self._r_list, self._w_list, self._x_list)
        # TODO: convert result into poll results
        return None

    def _add_fd(self, fd, mode):
        # TODO:
        pass

    def _modify_fd(self, fd, mode):
        # TODO:
        pass

    def _remove_fd(self, fd):
        # TODO:
        pass
