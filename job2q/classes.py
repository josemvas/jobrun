# -*- coding: utf-8 -*-
import os
from .utils import pathjoin
from .exceptions import NotAbsolutePath

class Identity(object):
    def __init__(self, obj):
        self.obj = obj
    def __eq__(self, other):
        return other is self.obj

class Bunch(dict):
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

class AbsPath(str):
    def __new__(cls, *args, expand=False):
        path = os.path.normpath(pathjoin(*args))
        if expand:
            path = os.path.expanduser(os.path.expandvars(path))
        if not os.path.isabs(path):
            raise NotAbsolutePath(path, 'is not an absolute path')
        obj = str.__new__(cls, path)
        obj.name = os.path.basename(path)
        obj.stem, obj.suffix = os.path.splitext(obj.name)
        return obj
    def parent(self):
        return AbsPath(os.path.dirname(self))
    def hasext(self, suffix):
        return self.suffix == suffix
    def exists(self):
        return os.path.exists(self)
    def isfile(self):
        return os.path.isfile(self)
    def isdir(self):
        return os.path.isdir(self)
    def listdir(self):
        return os.listdir(self)

