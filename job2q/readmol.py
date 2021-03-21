# -*- coding: utf-8 -*-
from job2q import messages

def readxyz(fh):
    coords = []
    try:
        natom = next(fh)
        try:
            natom = int(natom)
        except ValueError:
            messages.error('¡El archivo de coordenadas no tiene un formato válido!')
        title = next(fh)
        for line in range(natom):
            e, x, y, z, *_ = next(fh).split()
            coords.append((e, float(x), float(y), float(z)))
    except StopIteration:
        messages.error('¡El archivo de coordenadas termina antes de lo esperado!')
    for line in fh:
        if line:
            messages.error('¡El archivo de coordenadas no tiene un formato válido!')
    return {'natom':natom, 'title':title, 'coords':coords}
        

def readmol(fh):
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
    return {'natom':natom, 'title':title, 'coords':coords}

def readlog(fh):
    try:
        import cclib
    except ImportError:
        messages.error('Debe instalar cclib para poder leer el archivo de coordenadas')
    logfile = cclib.io.ccopen(fh)
    try:
        data = logfile.parse()
    except Exception:
        messages.error('¡El archivo de coordenadas no tiene un formato válido!')
    pt = cclib.parser.utils.PeriodicTable()
    natom = len(data.atomcoords[-1])
    title = data.scfenergies[-1]
    coords = [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]
    return {'natom':natom, 'title':title, 'coords':coords}


