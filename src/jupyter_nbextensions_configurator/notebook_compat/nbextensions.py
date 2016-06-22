# -*- coding: utf-8 -*-
"""Shim providing some notebook.nbextensions functions for versions < 4.2.0."""

# Original jupyter notebook source is
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import copy
import os

from jupyter_core.application import JupyterApp
from jupyter_core.paths import (
    ENV_CONFIG_PATH, SYSTEM_CONFIG_PATH, jupyter_config_dir,
)
from notebook import __version__
from notebook.nbextensions import ArgumentConflict
from tornado.log import LogFormatter
from traitlets import Bool

# Window doesn't support coloring in the commandline
GREEN_OK = '\033[32mOK\033[0m' if os.name != 'nt' else 'ok'
RED_X = '\033[31m X\033[0m' if os.name != 'nt' else ' X'

# -----------------------------------------------------------------------------
# The notebook public API is omitted.
# -----------------------------------------------------------------------------
# Applications. Many omitted from notebook version.
# -----------------------------------------------------------------------------


class BaseNBExtensionApp(JupyterApp):
    """Base nbextension installer app"""
    _log_formatter_cls = LogFormatter
    version = __version__

    flags = copy.deepcopy(JupyterApp.flags)
    flags.update({
        'user': ({
            'BaseNBExtensionApp': {
                'user': True,
            }}, 'Apply the operation only for the given user'
        ),
        'system': ({
            'BaseNBExtensionApp': {
                'user': False,
                'sys_prefix': False,
            }}, 'Apply the operation system-wide'
        ),
        'sys-prefix': ({
            'BaseNBExtensionApp': {
                'sys_prefix': True,
            }}, ('Use sys.prefix as the prefix for configuration operations ' +
                 'and installing nbextensions (for environments, packaging)')
        ),
        'py': ({
            'BaseNBExtensionApp': {
                'python': True,
            }}, 'Install from a Python package'
        )
    })
    flags['python'] = flags['py']
    flags.pop('y', None)
    flags.pop('generate-config', None)

    user = Bool(False, config=True, help="Whether to do a user install")
    sys_prefix = Bool(False, config=True,
                      help="Use the sys.prefix as the prefix")
    python = Bool(False, config=True, help="Install from a Python package")

    # stuff about verbose from notebook version omitted

    def _log_format_default(self):
        """A default format for messages"""
        return '%(message)s'

# -----------------------------------------------------------------------------
# Private API
# -----------------------------------------------------------------------------


def _get_config_dir(user=False, sys_prefix=False):
    """Get the location of config files for the current context

    Returns the string to the enviornment

    Parameters
    ----------

    user : bool [default: False]
        Get the user's .jupyter config directory
    sys_prefix : bool [default: False]
        Get sys.prefix, i.e. ~/.envs/my-env/etc/jupyter
    """
    user = False if sys_prefix else user
    if user and sys_prefix:
        raise ArgumentConflict(
            "Cannot specify more than one of user or sys_prefix")
    if user:
        nbext = jupyter_config_dir()
    elif sys_prefix:
        nbext = ENV_CONFIG_PATH[0]
    else:
        nbext = SYSTEM_CONFIG_PATH[0]
    return nbext
