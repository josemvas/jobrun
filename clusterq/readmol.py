#from logging import WARNING
from . import messages


class ParseError(Exception):
    def __init__(self, *message):
        super().__init__(' '.join(message))


# Guess format and read molfile
def readmol(molfile):
    if molfile.isfile():
        with open(molfile, mode='r') as fh:
            if molfile.hasext('.mol'):
                try:
                    return parsemdl(fh)
                except ParseError:
                    try:
                        return parsexyz(fh)
                    except ParseError:
                        messages.error(molfile, 'no es un archivo MDL ni XYZ válido')
            elif molfile.hasext('.xyz'):
                try:
                    return parsexyz(fh)
                except ParseError as e:
                    messages.error(molfile, 'no es un archivo XYZ válido', p(e))
            elif molfile.hasext('.log'):
                try:
                    return parseglf(fh)
                except ParseError:
                    messages.error(molfile, 'no es un archivo de salida de gaussian válido')
            else:
                messages.error('Solamente se pueden leer archivos mol, xyz y log')
    elif molfile.isdir():
        messages.error('El archivo', molfile, 'es un directorio')
    elif molfile.exists():
        messages.error('El archivo', molfile, 'no es regular')
    else:
        messages.error('El archivo', molfile, 'no existe')


# Parse XYZ molfile
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
            raise ParseError('Invalid format')
        try:
            title = next(fh)
            for line in range(natom):
                e, x, y, z, *_ = next(fh).split()
                coords.append((e, float(x), float(y), float(z)))
        except StopIteration:
            raise ParseError('Unexpected end of file')
        trajectory.append(coords)
        

# Parse MDL molfile
def parsemdl(fh):
    fh.seek(0)
    coords = []
    try:
        title = next(fh)
    except StopIteration:
        messages.error('El archivo de coordenadas está vacío')
    try:
        metadata = next(fh)
        comment = next(fh)
        natom, nbond, *_ = next(fh).split()
        try:
            natom = int(natom)
            nbond = int(nbond)
        except ValueError:
            raise ParseError('Invalid format')
        for _ in range(natom):
            x, y, z, e, *_ = next(fh).split()
            coords.append((e, float(x), float(y), float(z)))
        for _ in range(nbond):
            next(fh)
    except StopIteration:
        raise ParseError('Unexpected end of file')
    for line in fh:
        if line.split()[0] != 'M':
            raise ParseError('Invalid format')
    return [coords]


# Parse Gaussian logfile
def parseglf(fh):
    try:
        import cclib
    except ImportError:
        messages.error('Debe instalar cclib para poder leer el archivo de coordenadas')
    logfile = cclib.io.ccopen(fh)
#    logfile = cclib.io.ccopen(fh, loglevel=WARNING)
    try:
        data = logfile.parse()
    except Exception:
        raise ParseError('Invalid format')
    pt = cclib.parser.utils.PeriodicTable()
    return [(pt.element[data.atomnos[i]], e[0], e[1], e[2]) for i, e in enumerate(data.atomcoords[-1])]


