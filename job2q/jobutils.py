# -*- coding: utf-8 -*-
from os import path, getcwd
from . import messages
from .fileutils import AbsPath, NotAbsolutePath
from .utils import natsort

def printchoices(choices, indent=1, default=None):
    for choice in sorted(choices, key=natsort):
        if choice == default:
            print(' '*2*indent + choice + ' ' + '(default)')
        else:
            print(' '*2*indent + choice)

def findparameters(rootpath, pathparts, depth):
    part, key, default = pathparts[0]
    if key is None:
        rootpath = rootpath.joinpath(part)
    else:
        rootpath = rootpath.joinpath(part)
        try:
            diritems = rootpath.listdir()
        except FileNotFoundError:
            messages.cfgerror('El directorio', self, 'no existe')
        except NotADirectoryError:
            messages.cfgerror('La ruta', self, 'no es un directorio')
        if not diritems:
            messages.cfgerror('El directorio', self, 'está vacío')
        printchoices(choices=diritems, default=default, indent=depth-len(pathparts)+1)
        if pathparts[1:]:
            for item in diritems:
                listdir(rootpath.joinpath(item), pathparts[1:], depth)

def readmol(molfile, molname, keywords):
    if molfile:
        try:
            molfile = AbsPath(molfile)
        except NotAbsolutePath:
            molfile = AbsPath(getcwd(), molfile)
        if molfile.isfile():
            if molfile.hasext('.xyz'):
                for i, step in enumerate(readxyz(molfile), 1):
                    keywords['mol' + str(i)] = '\n'.join('{0:>2s}  {1:9.4f}  {2:9.4f}  {3:9.4f}'.format(*atom) for atom in step['coords'])
            else:
                messages.opterror('Solamente están soportados archivos de coordenadas en formato xyz')
        elif molfile.isdir():
            messages.opterror('El archivo de coordenadas', molfile, 'es un directorio')
        elif molfile.exists():
            messages.opterror('El archivo de coordenadas', molfile, 'no es un archivo regular')
        else:
            messages.opterror('El archivo de coordenadas', molfile, 'no existe')
        keywords['molfile'] = molfile
        molname = molfile.stem
    elif molname:
        keywords['molname'] = molname
    else:
        messages.opterror('Debe especificar el archivo de coordenadas o un nombre para interpolar el archivo de entrada')

