# -*- coding: utf-8 -*-
"""Shim providing notebook.nbextensions stuff from 4.2 for earlier versions."""

try:
    from notebook.nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
    )
except ImportError:
    from ._compat.nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
    )

__all__ = [
    'GREEN_OK', 'RED_X', 'BaseNBExtensionApp', '_get_config_dir',
]
