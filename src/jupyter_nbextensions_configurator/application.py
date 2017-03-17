# coding: utf-8
"""Utilities for installing jupyter_nbextensions_configurator."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import copy
import sys

from jupyter_contrib_core.notebook_compat import nbextensions, serverextensions

from jupyter_nbextensions_configurator import __version__


class ToggleJupyterNbextensionsConfiguratorApp(
        serverextensions.ToggleServerExtensionApp):
    """App to toggle server extension jupyter_nbextensions_configurator."""

    flags = copy.deepcopy(serverextensions.ToggleServerExtensionApp.flags)
    flags['sys-prefix'] = ({
        'ToggleServerExtensionApp': {
            'sys_prefix': True,
            'user': False,
        }},
        'Use sys.prefix as the prefix for configuring the server extension')
    for f in ('py', 'python'):
        flags.pop(f, None)

    def parse_command_line(self, argv=None):
        """
        Overriden to check for conflicting flags

        Since notebook version doesn't do it well (or, indeed, at all)
        """
        conflicting_flags = set(['--user', '--system', '--sys-prefix'])

        if len(conflicting_flags.intersection(set(argv))) > 1:
            raise serverextensions.ArgumentConflict(
                'cannot specify more than one of user, sys_prefix, or system')
        return super(ToggleJupyterNbextensionsConfiguratorApp,
                     self).parse_command_line(argv)

    @property
    def name(self):
        return 'jupyter_nbextensions_configurator {}'.format(
            'enable' if self._toggle_value else 'disable')

    @property
    def description(self):
        return """
{} the jupyter_nbextensions_configurator server extension in config.

Usage
    jupyter_nbextensions_configurator {} [--system|--sys-prefix|--user]
""".format(*(('Enable', 'enable')
             if self._toggle_value else ('Disable', 'disable')))

    def start(self):
        """Perform the App's actions as configured."""
        if self.extra_args:
            sys.exit('{} takes no extra arguments'.format(self.name))
        else:
            self.toggle_server_extension_python(
                'jupyter_nbextensions_configurator')
            nbexts = [
                ('notebook', 'nbextensions_configurator/config_menu/main'),
                ('tree', 'nbextensions_configurator/tree_tab/main'),
            ]
            for section, require in nbexts:
                enabled = self._toggle_value
                self.log.info('{} {} nbextension {}...'.format(
                    'Enabling' if enabled else 'Disabling', section, require))
                nbextensions._set_nbextension_state(
                    section, require, enabled,
                    user=self.user, sys_prefix=self.sys_prefix)


class EnableJupyterNbextensionsConfiguratorApp(
        ToggleJupyterNbextensionsConfiguratorApp):
    """App to enable server extension jupyter_nbextensions_configurator."""
    name = 'jupyter nbextensions_configurator enable'
    _toggle_value = True


class DisableJupyterNbextensionsConfiguratorApp(
        ToggleJupyterNbextensionsConfiguratorApp):
    """App to disable server extension jupyter_nbextensions_configurator."""
    name = 'jupyter nbextensions_configurator disable'
    _toggle_value = False


class JupyterNbextensionsConfiguratorApp(nbextensions.BaseNBExtensionApp):
    """Root level jupyter_nbextensions_configurator app."""

    name = 'jupyter nbextensions_configurator'
    version = __version__
    description = (
        'Enable or disable '
        'the jupyter_nbextensions_configurator server extension')
    subcommands = dict(
        enable=(
            EnableJupyterNbextensionsConfiguratorApp,
            'Enable the jupyter_nbextensions_configurator server extension.'),
        disable=(
            DisableJupyterNbextensionsConfiguratorApp,
            'Disable the jupyter_nbextensions_configurator server extension.'),
    )
    examples = '\n'.join([
        'jupyter nbextensions_configurator enable  # Enable the jupyter_nbextensions_configurator server extension.',  # noqa
        'jupyter nbextensions_configurator disable # Disable the jupyter_nbextensions_configurator server extension.',  # noqa
    ])

    def start(self):
        """Perform the App's actions as configured"""
        super(JupyterNbextensionsConfiguratorApp, self).start()

        # The above should have called a subcommand and raised NoStart; if we
        # get here, it didn't, so we should self.log.info a message.
        subcmds = ", ".join(sorted(self.subcommands))
        sys.exit("Please supply at least one subcommand: %s" % subcmds)


main = JupyterNbextensionsConfiguratorApp.launch_instance


if __name__ == '__main__':  # pragma: no cover
    main()
