import sys
assert sys.version_info >= (3, 4)
from job2q import console
try:
    console.install()
except KeyboardInterrupt:
    print('No se puede interrumpir la instalación')
