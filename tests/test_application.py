# -*- coding: utf-8 -*-
"""Tests for the main app."""

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import itertools
import json
import logging
import os
from unittest import TestCase

import jupyter_core.paths
import nose.tools as nt
from jupyter_contrib_core.notebook_compat import serverextensions
from jupyter_contrib_core.testing_utils import (
    get_logger, patch_traitlets_app_logs,
)
from jupyter_contrib_core.testing_utils.jupyter_env import patch_jupyter_dirs
from traitlets.config import Config
from traitlets.tests.utils import check_help_all_output, check_help_output

from jupyter_nbextensions_configurator.application import main as main_app
from jupyter_nbextensions_configurator.application import (
    DisableJupyterNbextensionsConfiguratorApp,
    EnableJupyterNbextensionsConfiguratorApp,
    JupyterNbextensionsConfiguratorApp,
)

app_classes = (DisableJupyterNbextensionsConfiguratorApp,
               EnableJupyterNbextensionsConfiguratorApp,
               JupyterNbextensionsConfiguratorApp)


def reset_app_class(app_class):
    """Reset all app traits and clear the instance."""
    if app_class._instance is None:
        return
    for name, traitlet in app_class._instance.traits().items():
        if isinstance(traitlet.this_class, JupyterNbextensionsConfiguratorApp):
            setattr(app_class._instance, name, traitlet.default_value)
    app_class.clear_instance()


class AppTest(TestCase):
    """Tests for the main app."""

    @classmethod
    def setup_class(cls):
        cls.log = cls.log = get_logger(cls.__name__)
        cls.log.handlers = []
        cls.log.propagate = True

    def setUp(self):
        """Set up test fixtures for each test."""
        (jupyter_patches, self.jupyter_dirs,
         remove_jupyter_dirs) = patch_jupyter_dirs()
        for ptch in jupyter_patches:
            ptch.start()
            self.addCleanup(ptch.stop)
        self.addCleanup(remove_jupyter_dirs)

        for klass in app_classes:
            patch_traitlets_app_logs(klass)
            klass.log_level.default_value = logging.DEBUG

    def check_enable(self, argv=None, dirs=None):
        """Check files were enabled in the correct place."""
        if argv is None:
            argv = []
        if dirs is None:
            dirs = {
                'conf': jupyter_core.paths.jupyter_config_dir(),
                'data': jupyter_core.paths.jupyter_data_dir(),
            }
        conf_dir = dirs['conf']

        # do enable
        main_app(argv=['enable'] + argv)

        # list everything that got enabled
        created_files = []
        for root, subdirs, files in os.walk(dirs['conf']):
            created_files.extend([os.path.join(root, f) for f in files])
        nt.assert_true(
            created_files,
            'enable should create files in {}'.format(dirs['conf']))

        # a bit of a hack to allow initializing a new app instance
        for klass in app_classes:
            reset_app_class(klass)

        # do disable
        main_app(argv=['disable'] + argv)
        # check the config directory
        conf_enabled = [
            path for path in created_files
            if path.startswith(conf_dir) and os.path.exists(path)]
        for path in conf_enabled:
            with open(path, 'r') as f:
                conf = Config(json.load(f))
            nbapp = conf.get('NotebookApp', {})
            nt.assert_not_in(
                'jupyter_nbextensions_configurator',
                nbapp.get('server_extensions', []),
                'conf after disable should empty'
                'server_extensions list'.format(path))
            nbservext = nbapp.get('nbserver_extensions', {})
            nt.assert_false(
                {k: v for k, v in nbservext.items() if v},
                'disable command should disable all '
                'nbserver_extensions in file {}'.format(path))

        reset_app_class(DisableJupyterNbextensionsConfiguratorApp)

    def test_00_extra_args(self):
        """Check that app complains about extra args."""
        for subcom in ('enable', 'disable'):
            # sys.exit should be called if extra args specified
            with nt.assert_raises(SystemExit):
                main_app([subcom, 'arbitrary_extension_name'])
            for klass in app_classes:
                reset_app_class(klass)

    def test_01_help_output(self):
        """Check that app help works."""
        app_module = 'jupyter_nbextensions_configurator.application'
        for argv in (['enable'], ['disable']):
            check_help_output(app_module, argv)
            check_help_all_output(app_module, argv)
        # sys.exit should be called if no argv specified
        with nt.assert_raises(SystemExit):
            main_app([])

    def test_02_default_enable(self):
        """Check that enable works correctly using defaults."""
        self.check_enable()

    def test_03_user_enable(self):
        """Check that enable works correctly using --user flag."""
        self.check_enable(argv=['--user'], dirs=self.jupyter_dirs['env_vars'])

    def test_04_sys_prefix_enable(self):
        """Check that enable works correctly using --sys-prefix flag."""
        self.check_enable(
            argv=['--sys-prefix'], dirs=self.jupyter_dirs['sys_prefix'])

    def test_05_system_enable(self):
        """Check that enable works correctly using --system flag."""
        self.check_enable(argv=['--system'], dirs=self.jupyter_dirs['system'])

    def test_06_argument_conflict(self):
        """Check that enable objects to multiple flags."""
        conflicting_flags = ('--user', '--system', '--sys-prefix')
        conflicting_flagsets = []
        for nn in range(2, len(conflicting_flags) + 1):
            conflicting_flagsets.extend(
                itertools.combinations(conflicting_flags, nn))
        for flagset in conflicting_flagsets:
            self.log.info('testing conflicting flagset {}'.format(flagset))
            nt.assert_raises(serverextensions.ArgumentConflict,
                             main_app, ['enable'] + list(flagset))
