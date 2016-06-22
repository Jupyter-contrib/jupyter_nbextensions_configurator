# -*- coding: utf-8 -*-
"""Shim providing notebook 4.2 extension stuff for use in earlier versions."""

try:
    from notebook.nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
    )
except ImportError:
    from .nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
    )

try:
    from notebook.serverextensions import (
        ToggleServerExtensionApp, toggle_serverextension_python,
    )
except ImportError:
    from .serverextensions import (
        ToggleServerExtensionApp, toggle_serverextension_python,
    )

__all__ = [
    '_get_config_dir',
    'BaseNBExtensionApp',
    'GREEN_OK',
    'RED_X',
    'toggle_serverextension_python',
    'ToggleServerExtensionApp',
]
