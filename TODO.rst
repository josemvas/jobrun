General
-------
- Mantener la carpeta de salida en el scratch si falla la copia al home
- Ignorar el known_hosts de los usuarios
- Trap para SIGINT y SIGTERM enviados por bkill
- Poner límite de memoria a los trabajos
- Agregar opción para imprimir la versión del programa
- Cambiar el mecanisno de generación de comentarios BSUB/SBATCH/PBS para soportar TORQUE

job2q
-----
- Move PYTHONPATH and SPECPATH from bash section to python section in job2q

console.py
----------
- Seleccionar el scheduler interactivamente

queue.py
----------
- Preguntar si se lanza el trabajo en caso de error al consultar su estado
- Checar el error estandar ademas de la salida estandar cuando no hay error

AbsPath
-------
- Considerar no aceptar listas de componentes de path como argumento (usar el método joinpath en su lugar)
- Considerar reemplazar método append con la opción keys=
- Change slash by comma to set interpolable path components with setkeys
