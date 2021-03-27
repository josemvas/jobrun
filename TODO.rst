General
-------
- Usar el modulo runutils en vez de bulletin
- Usar JSON5 en los archivos de especificaciones
- Add suport for dialog boxes (-X/--xdialog option)
- Validar los valores de nhost/hosts antes de enviar el trabajo
- Mantener la carpeta de salida en el scratch si falla la copia al home
- Ignorar el known_hosts de los usuarios
- Trap para SIGINT y SIGTERM enviados por bkill
- Poner límite de memoria a los trabajos
- Agregar opción para imprimir la versión del script
- Considerar no admitir componentes de ruta parcialmente interpolables y simplificar el código relacionado (setkeys, validate, yieldcomponents)
- Determinar los conjuntos de parámetros a partir del filtro, por ejemplo: autodock --addpath=$HOME/docklib/{release}/ligands/{ligand} --addpath=$HOME/docklib/{release}/receptors/{receptor} --release 1.1 --ligand=%1.pdbqt --receptor=%2 --filter '([^_]+)_([^_]+)'
- Agregar en las especificaciones de los trabajos un diccionario con las condiciones lógicas de los archivos de entrada y el mensaje de error si no se cumplen
- Nombrar la carpeta oculta de jobscripts con el número de trabajo
- Agregar una opción para incluir la clave y versión del programa en los nombres de los archivos de salida
- Considerar usar template strings para interpolar las opciones y especificaciones

console.py
----------
- Usar un menú interactivo para seleccionar el scheduler (y todas las demás opciones de configuración)
- Mover hostspec.json y queuespec.json dentro del directorio jobspecs y eliminar los links dentro de las carpetas de programa
- Manejar los permisos denegados cuando se instalan los programas

queue.py
----------
- Preguntar si se lanza el trabajo en caso de error al consultar su estado
- Checar el error estandar ademas de la salida estandar aunque no haya error

AbsPath
-------
- Considerar no aceptar listas de componentes de path como argumento (usar el método joinpath en su lugar)
- Quitar el método setkeys de Abspath y dejar a joinpath realizar la interpolacion de los componentes

readspec.py
-----------
- Revisar el método merge de SpecList
