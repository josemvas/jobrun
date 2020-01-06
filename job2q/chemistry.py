# -*- coding: utf-8 -*-
from job2q import messages

def readxyz(path):
    optrj = []
    with path.open(mode='r') as fh:
        while True:
            try:
                coords = [ ]
                natom = next(fh).strip()
                if natom.isdigit():
                    natom = int(natom)
                else:
                    messages.error('¡El archivo de coordenadas', path, 'no tiene un formato válido')
            except StopIteration:
                break
            try:
                title = next(fh).strip()
                for line in range(natom):
                    e, x, y ,z = next(fh).split()
                    coords.append((e, float(x), float(y), float(z)))
                optrj.append({'natom':natom, 'title':title, 'coords':coords})
            except StopIteration:
                messages.error('¡El archivo de coordenadas', path, 'termina antes de lo esperado!')
    return optrj

