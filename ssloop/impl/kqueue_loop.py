#!/usr/bin/python

import select


class SelectLoop(object):

    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def add_handler(self, handler):
        pass

    def add_timeout(self, timeout, handler):
        pass

    def add_fd(self, fd, mode, handler):
        pass

    def remove_fd(self, fd, mode, handler):
        pass
