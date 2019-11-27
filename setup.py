# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="job2queue",
    version="0.0.1",
    author="José Manuel Vásquez",
    author_email="manuelvsqz@gmail.com",
    description="Submit jobs to any computer cluster",
    long_description=open("README.rst").read(),
    long_description_content_type="text/x-rst",
    url="https://github.com/cronofugo/job2queue",
    packages=find_packages(),
    package_data={
        "job2queue": [
            "exec.py.txt",
            "database/platform/*/hostspecs.xml",
            "database/generic/*/jobspecs.xml",
            "database/platform/*/*/jobspecs.xml",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
#    python_requires=">=2.7",
    install_requires=[
        "future",
        "termcolor",
        "pyparsing",
        "bullet;python_version>='3.2'",
    ],
    entry_points={
        "console_scripts": [
            "j2q-setup=job2queue.main:setup",
        ],
    },
)
