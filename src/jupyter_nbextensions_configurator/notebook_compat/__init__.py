# -*- coding: utf-8 -*-
"""Shim providing notebook 4.2 extension stuff for use in earlier versions."""

try:
    from notebook.nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
        install_nbextension, install_nbextension_python, uninstall_nbextension,
        uninstall_nbextension_python,
    )
except ImportError:
    from .nbextensions import (
        GREEN_OK, RED_X, BaseNBExtensionApp, _get_config_dir,
        install_nbextension, install_nbextension_python, uninstall_nbextension,
        uninstall_nbextension_python,
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
    'install_nbextension',
    'install_nbextension_python',
    'RED_X',
    'toggle_serverextension_python',
    'ToggleServerExtensionApp',
    'uninstall_nbextension',
    'uninstall_nbextension_python',
]
