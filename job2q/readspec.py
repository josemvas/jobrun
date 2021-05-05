# -*- coding: utf-8 -*-
import json
from . import messages
from .utils import Bunch
from .details import dictags, listags

class SpecList(list):
    def __init__(self, plainlist=[]):
        for item in plainlist:
            if isinstance(item, dict):
                self.append(SpecBunch(item))
            elif isinstance(item, list):
                self.append(SpecList(item))
            else:
                self.append(item)
    def merge(self, other):
        for i in other:
            if i not in self:
                self.append(i)

class SpecBunch(Bunch):
    def __init__(self, plaindict={}):
        for key, value in plaindict.items():
            if isinstance(value, dict):
                self[key] = SpecBunch(value)
            elif isinstance(value, list):
                self[key] = SpecList(value)
            else:
                self[key] = value
    def __missing__(self, item):
        if item in dictags:
            return SpecBunch()
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

def readspec(jsonfile):
    with open(jsonfile, 'r') as fh:
        try: return SpecBunch(json.load(fh))
        except ValueError as e:
            messages.error('El archivo {} contiene JSON inválido: {}'.format(fh.name, str(e)))

