# -*- coding: utf-8 -*-
"""Shim providing notebook.serverextensions stuff for pre 4.2 versions."""

try:
    from notebook.serverextensions import (
        ToggleServerExtensionApp, toggle_serverextension_python,
    )
except ImportError:
    from ._compat.serverextensions import (
        ToggleServerExtensionApp, toggle_serverextension_python,
    )

__all__ = [
    'ToggleServerExtensionApp', 'toggle_serverextension_python',
]
