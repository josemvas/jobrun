import json5
from json5.model import Identifier
from json5.loader import DefaultLoader

class MyCustomLoader(DefaultLoader):
    @DefaultLoader.to_python(Identifier)
    def _(self, node):
        return str(node.name)

def json5_load(file):
    with open(file, 'r') as f:
        json_str = f.read()
    try:
        return json5.loads(json_str, loader=MyCustomLoader())
    except ValueError as e:
        messages.error(_('JSON inválido ($error) en $file'), error=str(e), file=f.name)
