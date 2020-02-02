# -*- coding: utf-8 -*-
from . import messages

class Bunch(dict):
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

class Identity(object):
    def __init__(self, ob):
        self.ob = ob
    def __eq__(self, other):
        return other is self.ob

