# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from xml.etree import ElementTree
from job2q.details import xmlListTags, xmlScriptTags, xmlDictTags, xmlProfileChildren, xmlTextTags
from job2q import messages

class BunchDict(dict):
    def __getattr__(self, attr):
        try: return self[attr]
        except KeyError:
            raise AttributeError(attr)
    def __missing__(self, key):
        if key in xmlListTags + xmlScriptTags:
            #self[key] = []
            #return self[key]
            return []

class ScriptTestDict(dict):
    def __init__(self, script='', boolean=True):
        self.script = script
        self.boolean = boolean
    def __bool__(self):
        return not self.boolean if 'not' in self else self.boolean
    __nonzero__ = __bool__
    def __str__(self):
        return self.script

class XmlTreeList(list):
    def __init__(self, parent):
        for child in parent:
            if not len(child):
                if child.tag == 'e':
                    if parent.tag in xmlScriptTags:
                        self.append(ScriptTestDict(script=child.text))
                        for attr in child.attrib:
                            self[-1][attr] = child.attrib[attr]
                    else:
                        self.append(child.text)
                elif child.tag in xmlProfileChildren:
                    self.append(xmlProfileChildren[child.tag] + ' ' + child.text)
                else:
                    raise Exception('Invalid XmlTreeList Tag <{0}>'.format(child.tag))
            else:
                raise Exception('XmlTreeList Tag <{0}> must not have grandchildren: <{0}>'.format(child.tag))
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


class XmlTreeDict(BunchDict):
    def __init__(self, parent):
        for child in parent:
            if len(child):
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = XmlTreeDict(child)
                    else:
                        raise Exception('XmlTreeDict Tag <e> must have a key attribute {0}'.format(parent))
                elif child.tag in xmlListTags + xmlScriptTags:
                    self[child.tag] = XmlTreeList(child)
                elif child.tag in xmlDictTags:
                    self[child.tag] = XmlTreeDict(child)
                elif child.tag in xmlTextTags:
                    raise Exception('XmlTreeDict Tag must <{0}> have grandchildren'.format(child.tag))
                else:
                    raise Exception('Invalid XmlTreeDict Tag {0} <{1}>'.format(parent, child.tag))
            else:
                if child.tag == 'e':
                    if 'key' in child.attrib:
                        self[child.attrib['key']] = child.text
                    else:
                        self[child.text] = child.text
                elif child.tag in xmlListTags + xmlScriptTags + xmlDictTags:
                    raise Exception('This XmlTreeList must not have grandchildren <{0}>'.format(child.tag))
                elif child.tag in xmlTextTags:
                    self[child.tag] = child.text
                else:
                    raise Exception('Invalid XmlTreeDict Tag {0} <{1}>'.format(parent, child.tag))
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

def readspec(xmlfile, xmltag=None):
    with open(xmlfile) as f:
        try: xmlroot = ElementTree.fromstringlist(['<root>', f.read(), '</root>'])
        except ElementTree.ParseError as e:
            messages.cfgerr('El archivo', xmlfile, 'no es válido:', str(e))
    if xmltag is None:
        return XmlTreeDict(xmlroot)
    else:
        try: return xmlroot.find(xmltag).text
        except AttributeError:
            return None

