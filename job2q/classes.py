# -*- coding: utf-8 -*-
from os.path import join, isabs, dirname, basename, normpath, expanduser, expandvars
from . import messages

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

class Path(str):
   def __new__(cls, *args):
      path = normpath(expanduser(expandvars(join(*args))))
      if not isabs(path):
          raise ValueError(path, 'is not an absolute path')
      return str.__new__(cls, path)
   def parent(self):
      return dirname(self)
   def stem(self):
      return basename(self)

