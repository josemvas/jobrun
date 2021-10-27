import sys
assert sys.version_info >= (3, 4)
from queuejob import console
try:
    console.install()
except KeyboardInterrupt:
    print('No se completó la instalación')
