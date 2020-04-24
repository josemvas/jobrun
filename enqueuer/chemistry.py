# -*- coding: utf-8 -*-
from enqueuer import messages

def readxyzfile(path):
    optrj = []
    with open(path, mode='r') as fh:
        while True:
            coords = [ ]
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

def readmolfile(path):
    optrj = []
    with open(path, mode='r') as fh:
        coords = [ ]
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
            optrj.append({'natom':natom, 'title':title, 'coords':coords})
            for line in range(nbond):
                next(fh)
        except StopIteration:
            messages.error('¡El archivo de coordenadas', path, 'termina antes de lo esperado!')
        while True:
            try:
                prop = next(fh)
                if prop.split()[0] != 'M':
                    messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
            except StopIteration:
                if prop.split() == [ 'M', 'END' ]:
                    break
                else:
                    messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido!')
    return optrj

