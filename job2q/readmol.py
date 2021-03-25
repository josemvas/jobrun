# -*- coding: utf-8 -*-
#from logging import WARNING
from job2q import messages


class ParseError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))


def readmolfile(molfile):
    if molfile.isfile():
        with open(molfile, mode='r') as fh:
            if molfile.hasext('.mol'):
                try:
                    return parsectf(fh)
                except ParseError:
                    try:
                        return parsexyz(fh)
                    except ParseError:
                        messages.error('El archivo', molfile, 'no es un archivo CTF o XYZ válido')
            elif molfile.hasext('.xyz'):
                try:
                    return parsexyz(fh)
                except ParseError:
                    messages.error('El archivo', molfile, 'no es un archivo XYZ válido')
            elif molfile.hasext('.log'):
                try:
                    return parselog(fh)
                except ParseError:
                    messages.error('El archivo', molfile, 'no es un archivo de Gaussian válido')
            else:
                messages.error('Solamente se pueden leer archivos mol, xyz y log')
    elif molfile.isdir():
        messages.error('El archivo', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo', molfile, 'no es regular')
    else:
        messages.error('El archivo', molfile, 'no existe')


def parsexyz(fh):
    fh.seek(0)
    trajectory = []
    while True:
        coords = []
        try:
            natom = next(fh)
        except StopIteration:
            if trajectory:
                return trajectory
            else:
                messages.error('El archivo de coordenadas está vacío')
        try:
            natom = int(natom)
        except ValueError:
            raise ParseError('El archivo de coordenadas no tiene un formato válido')
        try:
            title = next(fh)
            for line in range(natom):
                e, x, y, z, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
        except StopIteration:
            raise ParseError('El archivo de coordenadas termina antes de lo esperado')
        trajectory.append({'natom':natom, 'title':title, 'coords':coords})
        

def parsectf(fh):
    fh.seek(0)
    coords = []
    try:
        title = next(fh)
    except StopIteration:
        messages.error('¡El archivo de coordenadas está vacío!')
    try:
        metadata = next(fh)
        comment = next(fh)
        natom, nbond, *_ = next(fh).split()
        try:
            natom = int(natom)
            nbond = int(nbond)
        except ValueError:
            raise ParseError('El archivo de coordenadas no tiene un formato válido')
        for line in range(natom):
            x, y, z, e, *_ = next(fh).split()
            coords.append((e, float(x), float(y), float(z)))
        for line in range(nbond):
            next(fh)
    except StopIteration:
        raise ParseError('El archivo de coordenadas termina antes de lo esperado')
    for line in fh:
        if line.split()[0] != 'M':
            raise ParseError('El archivo de coordenadas no tiene un formato válido')
    if line.split()[1] != 'END':
        raise ParseError('El archivo de coordenadas no tiene un formato válido')
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
        messages.error('El archivo de coordenadas no tiene un formato válido')
    pt = cclib.parser.utils.PeriodicTable()
    natom = len(data.atomcoords[-1])
    title = data.scfenergies[-1]
    coords = [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]
    return [{'natom':natom, 'title':title, 'coords':coords}]


