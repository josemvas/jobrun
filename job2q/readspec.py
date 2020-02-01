# -*- coding: utf-8 -*-
import json
from . import messages
from .strings import listTags, dictTags, textTags
from .decorators import join_positional_args, pathseps

class BunchList(list):
    def __init__(self, parentlist):
        for item in parentlist:
            if isinstance(item, dict):
                self.append(Bunch(item))
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

class Bunch(dict):
    def __init__(self, parentdict):
        for key, value in parentdict.items():
            if isinstance(value, dict):
                self[key] = Bunch(value)
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
            return Bunch({})
        elif item in textTags:
            return ''
        else:
            messages.cfgerror('La propiedad', item, 'no puede faltar en el archivo de configuración')
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

def ordered(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, list):
        return sorted(ordered(x) for x in obj)
    else:
        return obj

@join_positional_args(pathseps)
def readspec(jsonfile):
    with open(jsonfile, 'r') as fh:
        try: return Bunch(ordered(json.load(fh)))
        except ValueError as e:
            messages.cfgerror('El archivo {} contiene JSON inválido: {}'.format(fh.name, str(e)))

