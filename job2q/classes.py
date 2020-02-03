# -*- coding: utf-8 -*-
from os import path, listdir
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
      filepath = path.normpath(pathjoin(*args))
      if expand:
          filepath = path.expanduser(path.expandvars(filepath))
      if not path.isabs(filepath):
          raise NotAbsolutePath(filepath, 'is not an absolute path')
      obj = str.__new__(cls, filepath)
      if obj != '/':
          obj.parent = AbsPath(path.dirname(filepath))
          obj.name = path.basename(filepath)
          obj.stem, obj.suffix = path.splitext(obj.name)
          return obj
   def hassuffix(suffix):
      return self.suffix == suffix
   def exists(self):
      return path.exists(self)
   def isfile(self):
      return path.isfile(self)
   def isdir(self):
      return path.isdir(self)
   def listdir(self):
      return listdir(self)

