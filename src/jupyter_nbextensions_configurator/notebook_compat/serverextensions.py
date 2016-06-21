# -*- coding: utf-8 -*-
"""
Functions from notebook.serverextensions for versions < 4.2.0.

Note that functions aren't quite direct copies, because of the switch from the
config key
NotebookApp.server_extensions (a list) in notebook < 4.2.0
to the key
NotebookApp.nbserver_extensions (a dict) in notebook >= 4.2.0
"""

# Original jupyter notebook source is
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import importlib

from jupyter_core.application import JupyterApp
from traitlets import Bool
from traitlets.config.manager import BaseJSONConfigManager
from traitlets.utils.importstring import import_item

try:
    from notebook.nbextensions import (
        _get_config_dir, BaseNBExtensionApp, GREEN_OK, RED_X,
    )
except ImportError:
    from .nbextensions import (
        _get_config_dir, BaseNBExtensionApp, GREEN_OK, RED_X,
    )


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

class ArgumentConflict(ValueError):
    pass


def toggle_serverextension_python(import_name, enabled=None, parent=None,
                                  user=True, sys_prefix=False, logger=None):
    """Toggle a server extension.

    By default, toggles the extension in the system-wide Jupyter configuration
    location (e.g. /usr/local/etc/jupyter).

    Parameters
    ----------

    import_name : str
        Importable Python module (dotted-notation) exposing the magic-named
        `load_jupyter_server_extension` function
    enabled : bool [default: None]
        Toggle state for the extension.  Set to None to toggle, True to enable,
        and False to disable the extension.
    parent : Configurable [default: None]
    user : bool [default: True]
        Toggle in the user's configuration location (e.g. ~/.jupyter).
    sys_prefix : bool [default: False]
        Toggle in the current Python environment's configuration location
        (e.g. ~/.envs/my-env/etc/jupyter). Will override `user`.
    logger : Jupyter logger [optional]
        Logger instance to use
    """
    user = False if sys_prefix else user
    config_dir = _get_config_dir(user=user, sys_prefix=sys_prefix)
    cm = BaseJSONConfigManager(parent=parent, config_dir=config_dir)
    cfg = cm.get("jupyter_notebook_config")
    server_extensions = (
        cfg.setdefault("NotebookApp", {})
        .setdefault("server_extensions", [])
    )

    old_enabled = import_name in server_extensions
    new_enabled = enabled if enabled is not None else not old_enabled

    if logger:
        if new_enabled:
            logger.info(u"Enabling: %s" % (import_name))
        else:
            logger.info(u"Disabling: %s" % (import_name))

    if new_enabled:
        if not old_enabled:
            server_extensions.append(import_name)
    elif old_enabled:
        while import_name in server_extensions:
            server_extensions.pop(server_extensions.index(import_name))

    if logger:
        logger.info(u"- Writing config: {}".format(config_dir))

    cm.update("jupyter_notebook_config", cfg)

    if new_enabled:
        validate_serverextension(import_name, logger)


def validate_serverextension(import_name, logger=None):
    """Assess the health of an installed server extension

    Returns a list of validation warnings.

    Parameters
    ----------

    import_name : str
        Importable Python module (dotted-notation) exposing the magic-named
        `load_jupyter_server_extension` function
    logger : Jupyter logger [optional]
        Logger instance to use
    """

    warnings = []
    infos = []

    func = None

    if logger:
        logger.info("    - Validating...")

    try:
        mod = importlib.import_module(import_name)
        func = getattr(mod, 'load_jupyter_server_extension', None)
    except Exception:  # pragma: no cover
        logger.warning("Error loading server extension %s", import_name)

    import_msg = u"     {} is {} importable?"
    if func is not None:
        infos.append(import_msg.format(GREEN_OK, import_name))
    else:  # pragma: no cover
        warnings.append(import_msg.format(RED_X, import_name))

    post_mortem = u"      {} {} {}"
    if logger:
        if warnings:  # pragma: no cover
            [logger.info(info) for info in infos]
            [logger.warn(warning) for warning in warnings]
        else:
            logger.info(post_mortem.format(import_name, "", GREEN_OK))

    return warnings

# ----------------------------------------------------------------------------
# Applications. Some from the notebook version of serverextensions are skipped
# ----------------------------------------------------------------------------

flags = {}
flags.update(JupyterApp.flags)
flags.pop('y', None)
flags.pop('generate-config', None)
flags.update({
    'user': ({
        'ToggleServerExtensionApp': {
            'user': True,
        }}, 'Perform the operation for the current user'
    ),
    'system': ({
        'ToggleServerExtensionApp': {
            'user': False,
            'sys_prefix': False,
        }}, 'Perform the operation system-wide'
    ),
    'sys-prefix': ({
        'ToggleServerExtensionApp': {
            'sys_prefix': True,
        }}, 'Use sys.prefix as the prefix for installing server extensions'
    ),
    'py': ({
        'ToggleServerExtensionApp': {
            'python': True,
        }}, 'Install from a Python package'
    ),
})
flags['python'] = flags['py']


class ToggleServerExtensionApp(BaseNBExtensionApp):
    """A base class for enabling/disabling extensions."""
    name = 'jupyter serverextension enable/disable'
    description = 'Enable/disable a server extension in config files.'

    aliases = {}
    flags = flags

    user = Bool(True, config=True, help='Whether to do a user install')
    sys_prefix = Bool(
        False, config=True, help='Use the sys.prefix as the prefix')
    python = Bool(False, config=True, help='Install from a Python package')

    def toggle_server_extension(self, import_name):
        """Change the status of a named server extension.

        Uses the value of `self._toggle_value`.

        Parameters
        ---------

        import_name : str
            Importable Python module (dotted-notation) exposing the magic-named
            `load_jupyter_server_extension` function
        """
        toggle_serverextension_python(
            import_name, self._toggle_value, parent=self, user=self.user,
            sys_prefix=self.sys_prefix, logger=self.log)

    def toggle_server_extension_python(self, package):
        """Change the status of some server extensions in a Python package.

        Uses the value of `self._toggle_value`.

        Parameters
        ---------

        package : str
            Importable Python module exposing the
            magic-named `_jupyter_server_extension_paths` function
        """
        m, server_exts = _get_server_extension_metadata(package)
        for server_ext in server_exts:
            module = server_ext['module']
            self.toggle_server_extension(module)

    # start definition omitted as it's overridden in
    # jupyter_nbextensions_configurator.application anyway

# -----------------------------------------------------------------------------
# Private API
# -----------------------------------------------------------------------------


def _get_server_extension_metadata(module):
    """Load server extension metadata from a module.

    Returns a tuple of (
        the package as loaded
        a list of server extension specs: [
            {
                "module": "mockextension"
            }
        ]
    )

    Parameters
    ----------

    module : str
        Importable Python module exposing the
        magic-named `_jupyter_server_extension_paths` function
    """
    m = import_item(module)
    if not hasattr(m, '_jupyter_server_extension_paths'):  # pragma: no cover
        raise KeyError(
            u'The Python module {} does not include any valid server extensions'.format(module))  # noqa
    return m, m._jupyter_server_extension_paths()
