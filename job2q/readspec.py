# -*- coding: utf-8 -*-
import json
from . import messages
from .strings import listTags, dictTags, textTags

class BunchList(list):
    def __init__(self, parentlist):
        for item in parentlist:
            if isinstance(item, dict):
                self.append(BunchDict(item))
            elif isinstance(item, list):
                self.append(BunchList(item))
            else:
                self.append(item)
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflicto en {} entre {} y {}'.format(i, self[i], other[i]))
            else:
                self.append(other[i])

class BunchDict(dict):
    def __init__(self, parentdict):
        for key, value in parentdict.items():
            if isinstance(value, dict):
                self[key] = BunchDict(value)
            elif isinstance(value, list):
                self[key] = BunchList(value)
            else:
                self[key] = value
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
    def __setattr__(self, item, value):
            self.__setitem__(item, value)
    def __missing__(self, item):
        if item in listTags:
            return BunchList([])
        elif item in dictTags:
            return BunchDict({})
        elif item in textTags:
            return ''
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflicto en {} entre {} y {}'.format(i, self[i], other[i]))
            else:
                self[i] = other[i]

def readspec(jsonfile, key=None):
    with open(jsonfile, 'r') as fh:
        if key is None:
            return BunchDict(json.load(fh))
        else:
            try: return json.load(fh)[key]
            except KeyError:
                return None

