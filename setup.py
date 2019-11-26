# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name="jobToQueue",
    version="0.0.1",
    author="José Manuel Vásquez",
    author_email="manuelvsqz@gmail.com",
    description="An unified command line tool to submit jobs to Torque, LSF or SLURM clusters",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/cronofugo/python-j2q",
    packages=setuptools.find_packages(),
    package_data={
        "jobToQueue": [
            "database/platform/*/hostspecs.xml",
            "database/generic/*/jobspecs.xml",
            "database/platform/*/*/jobpecs.xml",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=2.7",
    install_requires=[
        "future",
        "termcolor",
        "pyparsing",
        "bullet;python_version>='3.2'",
    ],
    entry_points={
        "console_scripts": [
            "j2q-setup=jobToQueue.main:setup",
        ],
    },
)
