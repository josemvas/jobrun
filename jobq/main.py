import os
import re
import sys
import json
from socket import gethostname
from clinterface import messages, _
from .shared import names, nodes, paths, environ, config, options
from .utils import ConfDict, LogDict, GlobDict, ConfigTemplate, InterpolationTemplate, option, natural_sorted as sorted, catch_keyboard_interrupt
from .fileutils import AbsPath, file_except_info
from .parsing import BoolParser
from .argparsing import parse_args
from .submission import configure_submission, submit_single_job

@catch_keyboard_interrupt
def submit_jobs(json_config):

    config.update(json.loads(json_config))
    names.command = os.path.basename(sys.argv[0])
    optiondict, argumentlist = parse_args(names, config)
    options.update(optiondict)
    configure_submission()

    if 'filter' in options.arguments:
        filtere = re.compile(options.arguments.filter)
    else:
        filtere = re.compile('.+')

    for inputfile in argumentlist:
        if options.common.job:
            workdir = AbsPath(options.common.cwd)
            for key in config.inputfiles:
                if (workdir/inputfile*key).isfile():
                    inputname = inputfile
                    break
            else:
                messages.failure(_('No hay archivos de entrada del trabajo $job', job=inputfile))
                continue
        else:
            path = AbsPath(inputfile, parent=options.common.cwd)
            try:
                path.assertfile()
            except Exception as e:
                file_except_info(e, path)
                continue
            for key in config.inputfiles:
                if path.name.endswith('.' + key):
                    inputname = path.name[:-len('.' + key)]
                    break
            else:
                messages.failure(_('$file no es un archivo de entrada de $program', file=path.name, program=config.progname))
                continue
            workdir = path.parent()
        filestatus = {}
        for key in config.filekeys:
            path = workdir/inputname-key
            filestatus[key] = path.isfile() #or key in options.restartfiles
        for conflict, message in config.conflicts.items():
            if BoolParser(conflict).evaluate(filestatus):
                messages.failure(InterpolationTemplate(message).safe_substitute(file=inputname))
                continue
        matched = filtere.fullmatch(inputname)
        if matched:
            filtergroups = {str(i): x for i, x in enumerate(matched.groups())}
            submit_single_job(workdir, inputname, filtergroups)

#if __name__ == '__main__':
#    run()
