# -*- coding: utf-8 -*-
"""Shim providing some notebook.nbextensions functions for versions < 4.2.0."""

# Original jupyter notebook source is
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import copy
import os
import shutil
import tarfile
import zipfile
from os.path import join as pjoin
from os.path import basename, normpath

from ipython_genutils.path import ensure_dir_exists
from ipython_genutils.py3compat import cast_unicode_py2
from ipython_genutils.tempdir import TemporaryDirectory
from jupyter_core.application import JupyterApp
from jupyter_core.paths import (
    ENV_CONFIG_PATH, ENV_JUPYTER_PATH, SYSTEM_CONFIG_PATH, SYSTEM_JUPYTER_PATH,
    jupyter_config_dir, jupyter_data_dir,
)
from notebook import __version__
from notebook.nbextensions import _safe_is_tarfile
from tornado.log import LogFormatter
from traitlets import Bool

try:
    # Py3
    from urllib.parse import urlparse
    from urllib.request import urlretrieve
except ImportError:
    # Py2
    from urlparse import urlparse
    from urllib import urlretrieve

DEPRECATED_ARGUMENT = object()

# Window doesn't support coloring in the commandline
GREEN_OK = '\033[32mOK\033[0m' if os.name != 'nt' else 'ok'
RED_X = '\033[31m X\033[0m' if os.name != 'nt' else ' X'

# -----------------------------------------------------------------------------
# Public API. Most of notebook public API is omitted
# -----------------------------------------------------------------------------


class ArgumentConflict(ValueError):
    pass


def install_nbextension(path, overwrite=False, symlink=False,
                        user=False, prefix=None, nbextensions_dir=None,
                        destination=None, verbose=DEPRECATED_ARGUMENT,
                        logger=None, sys_prefix=False
                        ):
    """Install a Javascript extension for the notebook

    Stages files and/or directories into the nbextensions directory.
    By default, this compares modification time, and only stages files that
    need updating.
    If `overwrite` is specified, matching files are purged before proceeding.

    Parameters
    ----------

    path : path to file, directory, zip or tarball archive, or URL to install
        By default, the file will be installed with its base name, so
        '/path/to/foo' will install to 'nbextensions/foo'. See the destination
        argument below to change this.
        Archives (zip or tarballs) will be extracted into the nbextensions
        directory.
    overwrite : bool [default: False]
        If True, always install the files, regardless of what may already be
        installed.
    symlink : bool [default: False]
        If True, create a symlink in nbextensions, rather than copying files.
        Not allowed with URLs or archives. Windows support for symlinks
        requires Vista or above, Python 3, and a permission bit which only
        admin users have by default, so don't rely on it.
    user : bool [default: False]
        Whether to install to the user's nbextensions directory.
        Otherwise do a system-wide install
        (e.g. /usr/local/share/jupyter/nbextensions).
    prefix : str [optional]
        Specify install prefix, if it should differ from default
        (e.g. /usr/local).
        Will install to ``<prefix>/share/jupyter/nbextensions``
    nbextensions_dir : str [optional]
        Specify absolute path of nbextensions directory explicitly.
    destination : str [optional]
        name the nbextension is installed to.
        For example, if destination is 'foo', then the source file will be
        installed to 'nbextensions/foo', regardless of the source name.
        This cannot be specified if an archive is given as the source.
    logger : Jupyter logger [optional]
        Logger instance to use
    """
    if verbose != DEPRECATED_ARGUMENT:
        import warnings
        warnings.warn(
            "`install_nbextension`'s `verbose` parameter is deprecated, it "
            "will have no effects and will be removed in Notebook 5.0",
            DeprecationWarning)

    # the actual path to which we eventually installed
    full_dest = None

    nbext = _get_nbextension_dir(
        user=user, sys_prefix=sys_prefix, prefix=prefix,
        nbextensions_dir=nbextensions_dir)
    # make sure nbextensions dir exists
    ensure_dir_exists(nbext)

    # forcing symlink parameter to False if os.symlink does not exist (e.g.,
    # on Windows machines running python 2)
    if not hasattr(os, 'symlink'):
        symlink = False

    if isinstance(path, (list, tuple)):
        raise TypeError(
            "path must be a string pointing to a single extension to install; "
            "call this function multiple times to install multiple extensions")

    path = cast_unicode_py2(path)

    if path.startswith(('https://', 'http://')):
        if symlink:
            raise ValueError("Cannot symlink from URLs")
        # Given a URL, download it
        with TemporaryDirectory() as td:
            filename = urlparse(path).path.split('/')[-1]
            local_path = os.path.join(td, filename)
            if logger:
                logger.info("Downloading: %s -> %s" % (path, local_path))
            urlretrieve(path, local_path)
            # now install from the local copy
            full_dest = install_nbextension(
                local_path, overwrite=overwrite, symlink=symlink,
                nbextensions_dir=nbext, destination=destination, logger=logger)
    elif path.endswith('.zip') or _safe_is_tarfile(path):
        if symlink:
            raise ValueError("Cannot symlink from archives")
        if destination:
            raise ValueError("Cannot give destination for archives")
        if logger:
            logger.info("Extracting: %s -> %s" % (path, nbext))

        if path.endswith('.zip'):
            archive = zipfile.ZipFile(path)
        elif _safe_is_tarfile(path):
            archive = tarfile.open(path)
        archive.extractall(nbext)
        archive.close()
        # TODO: what to do here
        full_dest = None
    else:
        if not destination:
            destination = basename(path)
        destination = cast_unicode_py2(destination)
        full_dest = normpath(pjoin(nbext, destination))
        if overwrite and os.path.lexists(full_dest):
            if logger:
                logger.info("Removing: %s" % full_dest)
            if os.path.isdir(full_dest) and not os.path.islink(full_dest):
                shutil.rmtree(full_dest)
            else:
                os.remove(full_dest)

        if symlink:
            path = os.path.abspath(path)
            if not os.path.exists(full_dest):
                if logger:
                    logger.info("Symlinking: %s -> %s" % (full_dest, path))
                os.symlink(path, full_dest)
        elif os.path.isdir(path):
            path = pjoin(os.path.abspath(path), '')  # end in path separator
            for parent, dirs, files in os.walk(path):
                dest_dir = pjoin(full_dest, parent[len(path):])
                if not os.path.exists(dest_dir):
                    if logger:
                        logger.info("Making directory: %s" % dest_dir)
                    os.makedirs(dest_dir)
                for file in files:
                    src = pjoin(parent, file)
                    dest_file = pjoin(dest_dir, file)
                    _maybe_copy(src, dest_file, logger=logger)
        else:
            src = path
            _maybe_copy(src, full_dest, logger=logger)

    return full_dest


# -----------------------------------------------------------------------------
# Applications. Many ommited from notebook version.
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


def _should_copy(src, dest, logger=None):
    """Should a file be copied, if it doesn't exist, or is newer?

    Returns whether the file needs to be updated.

    Parameters
    ----------

    src : string
        A path that should exist from which to copy a file
    src : string
        A path that might exist to which to copy a file
    logger : Jupyter logger [optional]
        Logger instance to use
    """
    if not os.path.exists(dest):
        return True
    if os.stat(src).st_mtime - os.stat(dest).st_mtime > 1e-6:
        # we add a fudge factor to work around a bug in python 2.x
        # that was fixed in python 3.x: http://bugs.python.org/issue12904
        if logger:
            logger.warn("Out of date: %s" % dest)
        return True
    if logger:
        logger.info("Up to date: %s" % dest)
    return False


def _maybe_copy(src, dest, logger=None):
    """Copy a file if it needs updating.

    Parameters
    ----------

    src : string
        A path that should exist from which to copy a file
    src : string
        A path that might exist to which to copy a file
    logger : Jupyter logger [optional]
        Logger instance to use
    """
    if _should_copy(src, dest, logger=logger):
        if logger:
            logger.info("Copying: %s -> %s" % (src, dest))
        shutil.copy2(src, dest)


def _get_nbextension_dir(user=False, sys_prefix=False, prefix=None,
                         nbextensions_dir=None):
    """Return the nbextension directory specified

    Parameters
    ----------

    user : bool [default: False]
        Get the user's .jupyter/nbextensions directory
    sys_prefix : bool [default: False]
        Get sys.prefix, i.e. ~/.envs/my-env/share/jupyter/nbextensions
    prefix : str [optional]
        Get custom prefix
    nbextensions_dir : str [optional]
        Get what you put in
    """
    if sum(map(bool, [user, prefix, nbextensions_dir, sys_prefix])) > 1:
        raise ArgumentConflict(
            "cannot specify more than one of user, sys_prefix, prefix, "
            "or nbextensions_dir")
    if user:
        nbext = pjoin(jupyter_data_dir(), u'nbextensions')
    elif sys_prefix:
        nbext = pjoin(ENV_JUPYTER_PATH[0], u'nbextensions')
    elif prefix:
        nbext = pjoin(prefix, 'share', 'jupyter', 'nbextensions')
    elif nbextensions_dir:
        nbext = nbextensions_dir
    else:
        nbext = pjoin(SYSTEM_JUPYTER_PATH[0], 'nbextensions')
    return nbext


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
