import sys
from .defs import colors
from .utils import join_args, join_args_and_kwargs, natsorted as sorted

@join_args_and_kwargs
def success(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors['green'] + message + colors['default'])

@join_args_and_kwargs
def warning(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors['yellow'] + message + colors['default'])

@join_args_and_kwargs
def failure(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    print(colors['red'] + message + colors['default'])

@join_args_and_kwargs
def error(message, details):
    if details:
        message = '{} ({})'.format(message, details)
    sys.exit(colors['red'] + message + colors['default'])

@join_args
def unknown_error(message):
    fcode = sys._getframe(1).f_code
    sys.exit(colors['red'] + '{}:{} {}'.format(fcode.co_filename, fcode.co_name, message) + colors['default'])

def excinfo(exception, path):
    if isinstance(exception, IsADirectoryError):
         failure('La ruta {} es un directorio'.format(path))
    elif isinstance(exception, NotADirectoryError):
         failure('La ruta {} no es un directorio'.format(path))
    elif isinstance(exception, FileExistsError):
         failure('El archivo o directorio {} ya existe'.format(path))
    elif isinstance(exception, FileNotFoundError):
         failure('El archivo o directorio {} no existe'.format(path))
    elif isinstance(exception, OSError):
         failure(str(exception).format(path))
    else:
         error('Tipo de excepción inesperada: {}'.format(type(exception).__name__))

def printtree(options, defaults=[], level=0):
    for opt in sorted(options):
        if defaults and opt == defaults[0]:
            print(' '*level + opt + '  (default)')
        else:
            print(' '*level + opt)
        if isinstance(options, dict):
            printtree(options[opt], defaults[1:], level + 1)

