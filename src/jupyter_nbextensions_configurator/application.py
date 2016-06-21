# coding: utf-8
"""Utilities for installing jupyter_nbextensions_configurator."""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import print_function

import copy
import operator
import sys

from jupyter_nbextensions_configurator import __version__
from jupyter_nbextensions_configurator.notebook_compat import (
    nbextensions, serverextensions,
)


class ToggleJupyterNbextensionsConfiguratorApp(
        serverextensions.ToggleServerExtensionApp):
    """An App that toggles the jupyter_nbextensions_configurator extension."""

    flags = copy.deepcopy(serverextensions.ToggleServerExtensionApp.flags)
    flags['sys-prefix'] = (
        flags['sys-prefix'][0],
        'Use sys.prefix as the prefix for configuring the server extension')
    for f in ('py', 'python'):
        flags.pop(f, None)

    @property
    def name(self):
        return 'jupyter_nbextensions_configurator {}'.format(
            'enable' if self._toggle_value else 'disable')

    @property
    def description(self):
        return """
Enable the jupyter_nbextensions_configurator server extension in configuration.

Usage
    jupyter_nbextensions_configurator {} [--system|--sys-prefix|--user]
""".format('Enable' if self._toggle_value else 'Disable')

    def start(self):
        """Perform the App's actions as configured."""
        if self.extra_args:
            sys.exit('{} takes no extra arguments'.format(self.name))
        else:
            self.toggle_server_extension_python(
                'jupyter_nbextensions_configurator')


class EnableJupyterNbextensionsConfiguratorApp(
        ToggleJupyterNbextensionsConfiguratorApp):
    """An App that enables the jupyter_nbextensions_configurator extension."""
    _toggle_value = True


class DisableJupyterNbextensionsConfiguratorApp(
        ToggleJupyterNbextensionsConfiguratorApp):
    """An App that disables the jupyter_nbextensions_configurator extension."""
    _toggle_value = False


class JupyterNbextensionsConfiguratorApp(nbextensions.BaseNBExtensionApp):
    """Root level jupyter_nbextensions_configurator app."""

    name = 'jupyter_nbextensions_configurator'
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
        '{} # {}'.format(appname, comment)
        for appname, comment in sorted(
            subcommands.values(), key=operator.itemgetter(1))
    ])

    def start(self):
        """Perform the App's actions as configured"""
        super(JupyterNbextensionsConfiguratorApp, self).start()

        # The above should have called a subcommand and raised NoStart; if we
        # get here, it didn't, so we should self.log.info a message.
        subcmds = ", ".join(sorted(self.subcommands))
        sys.exit("Please supply at least one subcommand: %s" % subcmds)


main = JupyterNbextensionsConfiguratorApp.launch_instance


if __name__ == '__main__':
    main()
