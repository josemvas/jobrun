# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import
from __future__ import division

import sys

class BoolOperand(object):
    def __init__(self, t, context):
        self.label = t[0]
        try:
            self.value = context[t[0]]
        except KeyError as e:
            sys.exit('(boolparse) undefined key: ' + e.args[0])
    def __bool__(self):
        return self.value
    def __str__(self):
        return self.label
    __repr__ = __str__
    __nonzero__ = __bool__

class BoolBinOp(object):
    def __init__(self, t):
        self.args = t[0][0::2]
    def __str__(self):
        sep = ' %s ' % self.reprsymbol
        return '(' + sep.join(map(str,self.args)) + ')'
    def __bool__(self):
        return self.evalop(bool(a) for a in self.args)
    __nonzero__ = __bool__
    __repr__ = __str__

class BoolAnd(BoolBinOp):
    reprsymbol = '&'
    evalop = all

class BoolOr(BoolBinOp):
    reprsymbol = '|'
    evalop = any

class BoolNot(object):
    def __init__(self, t):
        self.arg = t[0][1]
    def __bool__(self):
        v = bool(self.arg)
        return not v
    def __str__(self):
        return "~" + str(self.arg)
    __repr__ = __str__
    __nonzero__ = __bool__

#TODO: Implement default dict functionality to handle empty dicts without if testing
class Bunch(dict):
    def __init__(self, **kwargs):
        for key in kwargs:
            self[key] = kwargs[key]
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

#TODO: Implement iff attribute for e tag and remove d tag
class XmlTreeList(list):
    def __init__(self, parent):
        for child in parent:
            if not len(child):
                if child.tag == 'e':
                    self.append(child.text)
                elif child.tag == 's':
                    self.append(Bunch(repr=child.text))
                    for attr in child.attrib:
                        self[-1][attr] = child.attrib[attr]
                elif child.tag == 'export':
                    self.append('export' + ' ' + child.text)
                elif child.tag == 'source':
                    self.append('source' + ' ' + child.text)
                elif child.tag == 'load':
                    self.append('module' + ' ' + 'load' + ' ' + child.text)
                else:
                    sys.exit('(xmlparse) invalid tag: ' + child.tag)

class XmlTreeDict(dict):
    def __init__(self, parent):
        for child in parent:
            if len(child):
                if 'key' in child.attrib:
                    self[child.attrib['key']] = XmlTreeBunch(child)
            else:
                if 'key' in child.attrib:
                    self[child.attrib['key']] = child.text
                else:
                    self[child.text] = child.text

class XmlTreeBunch(Bunch):
    def __init__(self, parent):
        for child in parent:
            if len(child):
                if child.tag in ['inputfiles', 'outputfiles', 'positionargs', 'profile', 'parameteroot', 'prescript', 'postscript','offscript']:
                    self[child.tag] = XmlTreeList(child)
                elif child.tag in ['fileexts', 'filevars', 'optionargs', 'versionlist']:
                    self[child.tag] = XmlTreeDict(child)
                else:
                    self[child.tag] = XmlTreeBunch(child)
            else:
                if child.tag == 'init':
                    self.setdefault(child.tag, []).append(child.text)
                else:
                    self[child.tag] = child.text

