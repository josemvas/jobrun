# -*- coding: utf-8 -*-
from job2q import messages

def readxyz(path):
    optrj = []
    with open(path, mode='r') as fh:
        while True:
            coords = []
            try:
                natom = next(fh)
                try:
                    natom = int(natom)
                except ValueError:
                    messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
            except StopIteration:
                if optrj:
                    break
                else:
                    messages.error('¡El archivo de coordenadas', path, 'no contiene ninguna molécula!')
            try:
                title = next(fh)
                for line in range(natom):
                    e, x, y, z, *_ = next(fh).split()
                    coords.append((e, float(x), float(y), float(z)))
                optrj.append({'natom':natom, 'title':title, 'coords':coords})
            except StopIteration:
                messages.error('¡El archivo de coordenadas', path, 'termina antes de lo esperado!')
    return optrj

def readmol(path):
    with open(path, mode='r') as fh:
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
                messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
            for line in range(natom):
                x, y, z, e, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
            for line in range(nbond):
                next(fh)
        except StopIteration:
            messages.error('¡El archivo de coordenadas', path, 'termina antes de lo esperado!')
        while True:
            prop = next(fh)
            if prop.split()[0] != 'M':
                messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
        if prop.split() != [ 'M', 'END' ]:
            messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
    return [{'natom':natom, 'title':title, 'coords':coords}]

def readlog(path):
    try:
        import cclib
    except ImportError:
        messages.error('Debe instalar cclib para poder leer el archivo', path)
    print(path)
    logfile = cclib.io.ccopen(path)
    try:
        data = logfile.parse()
    except Exception:
        messages.error('Ocurrió un error analizando el formato del archivo', path)
    pt = cclib.parser.utils.PeriodicTable()
    natom = len(data.atomcoords[-1])
    title = data.scfenergies[-1]
    coords = [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]
    return [{'natom':natom, 'title':title, 'coords':coords}]


