# -*- coding: utf-8 -*-
from xml.etree import ElementTree

from . import messages
from .strings import listTags, dictTags, optionTags, commandTags, textTags

class XmlTreeList(list):
    def __init__(self, parent):
        for child in parent:
            if not len(child):
                if child.tag == 'e':
                    self.append(child.text)
                elif child.tag in commandTags:
                    self.append(commandTags[child.tag] + ' ' + child.text)
                else:
                    messages.cfgerror('Invalid XmlTreeList Tag <{0}><{1}>'.format(parent.tag, child.tag))
            else:
                messages.cfgerror('XmlTreeList Tag <{0}><{1}> must not have grandchildren'.format(parent.tag, child.tag))
    def merge(self, other):
        for i in other:
            if i in self:
                if hasattr(self[i], 'merge') and type(other[i]) is type(self[i]):
                    self[i].merge(other[i])
                elif other[i] == self[i]:
                    pass # same leaf value
                else:
                    raise Exception('Conflict at' + ' ' + str(i))
            else:
                self.append(other[i])

class BunchDict(dict):
    def __getattr__(self, item):
        try: return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)
    def __setattr__(self, item, value):
            self.__setitem__(item, value)
    def __missing__(self, item):
        return BunchDict()

class XmlTreeDict(BunchDict):
    def __init__(self, parent):
        for child in parent:
            if len(child):
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = XmlTreeDict(child)
                    else:
                        messages.cfgerror('XmlTreeDict Tag <{0}><e> must have a key attribute'.format(parent.tag))
                elif child.tag in listTags:
                    self[child.tag] = XmlTreeList(child)
                elif child.tag in dictTags:
                    self[child.tag] = XmlTreeDict(child)
                else:
                    messages.cfgerror('Invalid XmlTreeDict Tag <{0}><{1}>'.format(parent.tag, child.tag))
            else:
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = child.text
                elif child.tag in textTags or parent.tag in optionTags:
                    self[child.tag] = child.text
                else:
                    messages.cfgerror('Invalid XmlTreeDict Tag <{0}><{1}>'.format(parent.tag, child.tag))
    def __missing__(self, item):
        if item in listTags:
            return []
        elif item in dictTags:
            return BunchDict()
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
                    raise Exception('Conflict at' + ' ' + str(i))
            else:
                self[i] = other[i]

def readxmlspec(xmlfile, xmltag=None):
    root = ElementTree.parse(xmlfile).getroot()
    if xmltag is None:
        return XmlTreeDict(root)
    else:
        try: return root.find(xmltag).text
        except AttributeError:
            return None

