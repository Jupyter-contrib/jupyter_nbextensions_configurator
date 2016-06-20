# -*- coding: utf-8 -*-
"""Functions from notebook.serverextensions for versions < 4.2.0."""

# Original jupyter notebook source is
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import importlib

try:
    from notebook.nbextensions import _get_config_dir, GREEN_OK, RED_X
except ImportError:
    from .nbextensions import _get_config_dir, GREEN_OK, RED_X

from traitlets.utils.importstring import import_item
from traitlets.config.manager import BaseJSONConfigManager


# ------------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------------
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
        .setdefault("nbserver_extensions", {})
    )

    old_enabled = server_extensions.get(import_name, None)
    new_enabled = enabled if enabled is not None else not old_enabled

    if logger:
        if new_enabled:
            logger.info(u"Enabling: %s" % (import_name))
        else:
            logger.info(u"Disabling: %s" % (import_name))

    server_extensions[import_name] = new_enabled

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
    except Exception:
        logger.warning("Error loading server extension %s", import_name)

    import_msg = u"     {} is {} importable?"
    if func is not None:
        infos.append(import_msg.format(GREEN_OK, import_name))
    else:
        warnings.append(import_msg.format(RED_X, import_name))

    post_mortem = u"      {} {} {}"
    if logger:
        if warnings:
            [logger.info(info) for info in infos]
            [logger.warn(warning) for warning in warnings]
        else:
            logger.info(post_mortem.format(import_name, "", GREEN_OK))

    return warnings

# ------------------------------------------------------------------------------
# Private API
# ------------------------------------------------------------------------------


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
    if not hasattr(m, '_jupyter_server_extension_paths'):
        raise KeyError(
            u'The Python module {} does not include any valid server extensions'.format(module))  # noqa
    return m, m._jupyter_server_extension_paths()
