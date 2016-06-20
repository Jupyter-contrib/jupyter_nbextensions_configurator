# -*- coding: utf-8 -*-
"""Shim providing notebook 4.2 extension stuff for use in earlier versions."""

try:
    from notebook.nbextensions import (
        install_nbextension, install_nbextension_python, uninstall_nbextension,
        uninstall_nbextension_python,
    )
except ImportError:
    from .nbextensions import (
        install_nbextension, install_nbextension_python, uninstall_nbextension,
        uninstall_nbextension_python,
    )

try:
    from notebook.serverextensions import toggle_serverextension_python
except ImportError:
    from .serverextensions import toggle_serverextension_python

__all__ = [
    'install_nbextension',
    'install_nbextension_python',
    'uninstall_nbextension',
    'uninstall_nbextension_python',
    'toggle_serverextension_python',
]
