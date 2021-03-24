# -*- coding: utf-8 -*-
#from logging import WARNING
from job2q import messages

def readmolfile(molfile):
    if molfile.hasext('.mol'):
        reader = parsemdlmol
    elif molfile.hasext('.xyz'):
        reader = parsexyz
    elif molfile.hasext('.log'):
        reader = readlog
    else:
        messages.error('Solamente se pueden leer archivos mol, xyz y log')
    if molfile.isfile():
        with open(molfile, mode='r') as fh:
            return reader(fh)
    elif molfile.isdir():
        messages.error('El archivo de coordenadas', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo de coordenadas', molfile, 'no es un archivo regular')
    else:
        messages.error('El archivo de coordenadas', molfile, 'no existe')


def parsexyz(fh):
    trajectory = []
    while True:
        coords = []
        try:
            natom = next(fh)
        except StopIteration:
            if trajectory:
                return trajectory
            else:
                messages.error('¡El archivo de coordenadas está vacío!')
        try:
            natom = int(natom)
        except ValueError:
            messages.error('¡El archivo de coordenadas no tiene un formato válido!')
        try:
            title = next(fh)
            for line in range(natom):
                e, x, y, z, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
        except StopIteration:
            messages.error('¡El archivo de coordenadas termina antes de lo esperado!')
        trajectory.append({'natom':natom, 'title':title, 'coords':coords})
        

def parsemdlmol(fh):
    coords = []
    try:
        title = next(fh)
        metadata = next(fh)
        comment = next(fh)
        natom, nbond, *_ = next(fh).split()
        try:
            natom = int(natom)
            nbond = int(nbond)
        except ValueError:
            messages.error('¡El archivo de coordenadas no tiene un formato válido!')
        for line in range(natom):
            x, y, z, e, *_ = next(fh).split()
            coords.append((e, float(x), float(y), float(z)))
        for line in range(nbond):
            next(fh)
    except StopIteration:
        messages.error('¡El archivo de coordenadas termina antes de lo esperado!')
    for line in fh:
        if line.split()[0] != 'M':
            messages.error('¡El archivo de coordenadas no tiene un formato válido!')
    if line.split()[1] != 'END':
        messages.error('¡El archivo de coordenadas no tiene un formato válido!')
    return [{'natom':natom, 'title':title, 'coords':coords}]

def parsegausslog(fh):
    try:
        import cclib
    except ImportError:
        messages.error('Debe instalar cclib para poder leer el archivo de coordenadas')
    logfile = cclib.io.ccopen(fh)
#    logfile = cclib.io.ccopen(fh, loglevel=WARNING)
    try:
        data = logfile.parse()
    except Exception:
        messages.error('¡El archivo de coordenadas no tiene un formato válido!')
    pt = cclib.parser.utils.PeriodicTable()
    natom = len(data.atomcoords[-1])
    title = data.scfenergies[-1]
    coords = [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]
    return [{'natom':natom, 'title':title, 'coords':coords}]


