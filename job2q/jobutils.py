# -*- coding: utf-8 -*-
from os import getcwd
from . import messages
from .utils import natsort
from .fileutils import AbsPath, NotAbsolutePath, diritems
from .chemistry import readxyzfile, readmolfile

class NonMatchingFile(Exception):
    pass

class InputFileError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def printchoices(choices, indent=1, default=None):
    for choice in natsort(choices):
        if choice == default:
            print(' '*2*indent + choice + ' '*2 + '[default]')
        else:
            print(' '*2*indent + choice)

def findparameters(rootpath, components, defaults, indent):
    component = next(components, None)
    if component:
        try:
            findparameters(rootpath.joinpath(component.format()), components, defaults, indent)
        except IndexError:
            choices = diritems(rootpath, component)
            try:
                default = component.format(*defaults)
            except IndexError:
                default = None
            printchoices(choices=choices, default=default, indent=indent)
            for choice in choices:
                findparameters(rootpath.joinpath(choice), components, defaults, indent + 1)
            
def readcoords(options):
    molfile = AbsPath(molfile, cwdir=getcwd())
    molformat = '{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format
    if molfile.isfile():
        if molfile.hasext('.xyz'):
            for i, step in enumerate(readxyzfile(molfile), 1):
                options.keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
        elif molfile.hasext('.mol'):
            for i, step in enumerate(readmolfile(molfile), 1):
                options.keywords['mol' + str(i)] = '\n'.join(molformat(*atom) for atom in step['coords'])
        else:
            messages.error('Solamente están soportados archivos de coordenadas en formato XYZ o MOL')
    elif molfile.isdir():
        messages.error('El archivo de coordenadas', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
    else:
        messages.error('El archivo de coordenadas', molfile, 'no existe')
    options.keywords.molfile = molfile

