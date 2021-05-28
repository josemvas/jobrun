# -*- coding: utf-8 -*-
import json
from collections import OrderedDict
from . import messages
from .details import dictags, listags

class SpecList(list):
    def __init__(self, plainlist=[]):
        for item in plainlist:
            if isinstance(item, dict):
                self.append(SpecDict(item))
            elif isinstance(item, list):
                self.append(SpecList(item))
            else:
                self.append(item)
    def merge(self, other):
        for i in other:
            if i not in self:
                self.append(i)

class SpecDict(OrderedDict):
    def __init__(self, plaindict={}):
        super().__init__()
        for key, value in plaindict.items():
            if isinstance(value, dict):
                self[key] = SpecDict(value)
            elif isinstance(value, list):
                self[key] = SpecList(value)
            else:
                self[key] = value
    def __missing__(self, item):
        if item in dictags:
            return SpecDict()
        elif item in listags:
            return SpecList()
        else:
            raise AttributeError()
    def merge(self, other):
        for i in other:
            if i in self:
                if type(other[i]) is type(self[i]):
                    if hasattr(self[i], 'merge'):
                        self[i].merge(other[i])
                    elif self[i] != other[i]:
                        # Overwrite value if differ
                        self[i] = other[i]
                # Raise exception if type conflicts
                else:
                   raise Exception('Conflicto en {} entre {} y {}'.format(i, self[i], other[i]))
            else:
                self[i] = other[i]
    def __getattr__(self, name):
        if not name.startswith('_'):
            return self[name]
        super(SpecDict, self).__getattr__(name)
    def __setattr__(self, name, value):
        if not name.startswith('_'):
            self[name] = value
        else:
            super(SpecDict, self).__setattr__(name, value)


def readspec(jsonfile):
    with open(jsonfile, 'r') as f:
        try:
            return SpecDict(json.load(f, object_pairs_hook=OrderedDict))
        except ValueError as e:
            messages.error('El archivo {} contiene JSON inválido: {}'.format(f.name, str(e)))

