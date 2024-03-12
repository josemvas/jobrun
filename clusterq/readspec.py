import pyjson5 as json5
from collections import OrderedDict
from clinterface import messages, _

class SpecList(list):
    def __init__(self, *args):
        for item in args:
            if isinstance(item, dict):
                self.append(SpecDict(**item))
            elif isinstance(item, list):
                self.append(SpecList(*item))
            elif item is None or isinstance(item, str):
                self.append(item)
            else:
                raise ValueError('Invalid data type')
    def merge(self, other):
        for i in other:
            if i not in self:
                self.append(i)

class SpecDict(OrderedDict):
    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if isinstance(value, dict):
                self[key] = SpecDict(**value)
            elif isinstance(value, list):
                self[key] = SpecList(*value)
            elif value is None or isinstance(value, str):
                self[key] = value
            else:
                raise ValueError('Invalid data type')
    def merge(self, other):
        for i in other:
            if i in self and hasattr(self[i], 'merge'):
                self[i].merge(other[i])
            # Update existing entry or append new one
            else:
                self[i] = other[i]
    def __getattr__(self, key):
        if key.startswith('_'):
            return super(SpecDict, self).__getattr__(key)
        else:
            try:
                return self[key]
            except KeyError:
                raise AttributeError(key)
    def __setattr__(self, key, value):
        if key.startswith('_'):
            super(SpecDict, self).__setattr__(key, value)
        else:
            self[key] = value


def readspec(file):
    with open(file, 'r') as f:
        try:
            return SpecDict(**json5.load(f, object_pairs_hook=OrderedDict))
        except ValueError as e:
            messages.error('El archivo $file contiene JSON inválido', str(e), file=f.name)
