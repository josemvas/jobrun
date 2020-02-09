# -*- coding: utf-8 -*-
from os import path, getcwd
from . import messages
from .jobparse import run, jobspecs, keywords
from .fileutils import AbsPath, NotAbsolutePath, pathjoin
from .utils import q

class InputFileError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))

def nextfile():

    file = run.files.pop(0)

    try:
        filepath = AbsPath(file)
    except NotAbsolutePath:
        filepath = AbsPath(getcwd(), file)

    inputdir = filepath.parent()
    basename = filepath.name
    
    if filepath.isfile():
        for key in (k for i in jobspecs.inputfiles for k in i.split('|')):
            if basename.endswith('.' + key):
                inputname = basename[:-len(key)-1]
                inputext = key
                break
        else:
            raise InputFileError('Este trabajo no se envió porque el archivo de entrada', basename, 'no está asociado a', jobspecs.progname)
    elif filepath.isdir():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'es un directorio')
    elif filepath.exists():
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no es un archivo regular')
    else:
        raise InputFileError('Este trabajo no se envió porque el archivo de entrada', filepath, 'no existe')

    if run.interpolate:
        templatename = inputname
        inputname = '.'.join((run.molname, inputname))
        for item in jobspecs.inputfiles:
            for key in item.split('|'):
                if path.isfile(pathjoin(inputdir, (templatename, key))):
                    with open(pathjoin(inputdir, (templatename, key)), 'r') as fr, open(pathjoin(inputdir, (inputname, key)), 'w') as fw:
                        try:
                            fw.write(fr.read().format(**keywords))
                        except KeyError as e:
                            raise InputFileError('No se definió la variable de interpolación', q(e.args[0]), 'del archivo de entrada', pathjoin((templatename, key)))

    return inputdir, inputname, inputext

