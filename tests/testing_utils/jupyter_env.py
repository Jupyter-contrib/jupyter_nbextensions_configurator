# -*- coding: utf-8 -*-
"""Functions for patching jupyter env vars & paths."""

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import os
import shutil
import sys
import tempfile

import jupyter_core.paths

from jupyter_nbextensions_configurator.notebook_compat import nbextensions
from testing_utils import stringify_env

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # py2


def make_dirs(test_dir, base_dir):
    """Return a dict of root, config and data directory paths."""
    dirs = {
        'root': os.path.join(test_dir, base_dir),
        'conf': os.path.join(test_dir, base_dir, 'config'),
        'data': os.path.join(test_dir, base_dir, 'data'),
    }
    if not os.path.exists(dirs['root']):
        os.makedirs(dirs['root'])
    return dirs


def patch_jupyter_dirs():
    """
    Patch jupyter paths to use temporary directories.

    This just creates the patches and directories, caller is still
    responsible for starting & stopping patches, and removing temp dir when
    appropriate.
    """
    test_dir = tempfile.mkdtemp(prefix='jupyter_')
    jupyter_dirs = {name: make_dirs(test_dir, name) for name in (
        'user_home', 'env_vars', 'system', 'sys_prefix', 'custom', 'server')}
    jupyter_dirs['root'] = test_dir

    for name in ('notebook', 'runtime'):
        d = jupyter_dirs['server'][name] = os.path.join(
            test_dir, 'server', name)
        if not os.path.exists(d):
            os.makedirs(d)

    # patch relevant environment variables
    jupyter_patches = []
    jupyter_patches.append(
        patch.dict('os.environ', stringify_env({
            'HOME': jupyter_dirs['user_home']['root'],
            'JUPYTER_CONFIG_DIR': jupyter_dirs['env_vars']['conf'],
            'JUPYTER_DATA_DIR': jupyter_dirs['env_vars']['data'],
        })))

    # patch jupyter path variables in various modules
    # find the appropriate modules to patch according to compat.
    # Should include either
    # notebook.nbextensions
    # or
    # jupyter_nbextensions_configurator.notebook_compat._compat.nbextensions
    modules_to_patch = (
        jupyter_core.paths,
        sys.modules[nbextensions._get_config_dir.__module__])
    path_patches = dict(
        SYSTEM_CONFIG_PATH=[jupyter_dirs['system']['conf']],
        ENV_CONFIG_PATH=[jupyter_dirs['sys_prefix']['conf']],
        SYSTEM_JUPYTER_PATH=[jupyter_dirs['system']['data']],
        ENV_JUPYTER_PATH=[jupyter_dirs['sys_prefix']['data']],
    )
    for mod in modules_to_patch:
        applicable_patches = {
            attrname: newval for attrname, newval in path_patches.items()
            if hasattr(mod, attrname)}
        jupyter_patches.append(
            patch.multiple(mod, **applicable_patches))

    def remove_jupyter_dirs():
        """Remove all temporary directories created."""
        shutil.rmtree(test_dir)

    return jupyter_patches, jupyter_dirs, remove_jupyter_dirs
