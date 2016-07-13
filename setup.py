#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup script for jupyter_nbextensions_configurator."""

from __future__ import print_function

import os
from glob import glob

from setuptools import find_packages, setup


def main():

    setup(
        name='jupyter_nbextensions_configurator',
        description=("jupyter serverextension providing configuration "
                     "interfaces for nbextensions."),
        long_description="""
The jupyter_nbextensions_configurator jupyter server extension provides
graphical user interfaces for configuring which nbextensions are enabled (load
automatically for every notebook), and display their readme files.
In addition, for extensions which include an appropriate yaml descriptor file,
the interface also provides controls to configure the extensions' options.
""",
        version='0.2.1',
        author='jcb91, jupyter-contrib developers',
        author_email='joshuacookebarnes@gmail.com',
        url=('https://github.com/'
             'jupyter-contrib/jupyter_nbextensions_configurator'),
        download_url=('https://github.com/'
                      'jupyter-contrib/jupyter_nbextensions_configurator/'
                      'tarball/0.2.1'),
        keywords=['Jupyter', 'notebook'],
        license='BSD 3-clause',
        platforms=['any'],
        packages=find_packages('src'),
        package_dir={'': 'src'},
        include_package_data=True,
        py_modules=[
            os.path.splitext(os.path.basename(path))[0]
            for path in glob('src/*.py')
        ],
        install_requires=[
            'jupyter_contrib_core >=0.2',
            'jupyter_core',
            'notebook >=4.0',
            'pyyaml',
            'tornado',
            'traitlets',
        ],
        extras_require={
            'test': [
                'jupyter_contrib_core[testing_utils]',
                'nose',
                'requests',
                'selenium',
            ],
            'test:python_version == "2.7"': [
                'mock',
            ],
        },
        # we can't be zip safe as we require templates etc to be accessible to
        # jupyter server
        zip_safe=False,
        entry_points={
            'console_scripts': [
                'jupyter-nbextensions_configurator = jupyter_nbextensions_configurator.application:main',  # noqa
            ],
        },
        scripts=[os.path.join('scripts', p) for p in [
            'jupyter-nbextensions_configurator',
        ]],
        classifiers=[
            'Intended Audience :: End Users/Desktop',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: BSD License',
            'Natural Language :: English',
            'Operating System :: OS Independent',
            'Programming Language :: JavaScript',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Topic :: Utilities',
        ],
    )

if __name__ == '__main__':
    main()
