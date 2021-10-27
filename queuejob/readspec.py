import json
from collections import OrderedDict
from . import messages

class SpecList(list):
    def __init__(self, rawlist=[]):
        for item in rawlist:
            if isinstance(item, dict):
                self.append(SpecDict(item))
            elif isinstance(item, list):
                self.append(SpecList(item))
            elif isinstance(item, str):
                self.append(item)
            else:
                raise ValueError('Invalid data type')
    def merge(self, other):
        for i in other:
            if i not in self:
                self.append(i)

class SpecDict(OrderedDict):
    def __init__(self, rawdict={}):
        super().__init__()
        for key, value in rawdict.items():
            if isinstance(value, dict):
                self[key] = SpecDict(value)
            elif isinstance(value, list):
                self[key] = SpecList(value)
            elif isinstance(value, str):
                self[key] = value
            else:
                raise ValueError('Invalid data type')
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge'):
                    self[i].merge(other[i])
                elif self[i] != other[i]:
                    # Throw error if values differ
                    raise Exception('self[{1}]={2} /= other[{1}]={3}'.format(i, self[i], other[i]))
                    # Overwrite if values differ
#                        self[i] = other[i]
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


def readspec(jsonfile):
    with open(jsonfile, 'r') as f:
        try:
            return SpecDict(json.load(f, object_pairs_hook=OrderedDict))
        except ValueError as e:
            messages.error('El archivo {} contiene JSON inválido: {}'.format(f.name, str(e)))

