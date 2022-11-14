# -*- coding: utf-8 -*-
# - Copyright (c) 2001-2016, IPython-Contrib Development Team
# - Copyright (c) 2016-, jupyter-contrib development team

"""Jupyter server extension to enable, disable and configure nbextensions."""

from __future__ import unicode_literals

import io
import json
import logging
import os.path
import posixpath
import re

import yaml
from notebook import version_info as nb_version_info
from notebook.base.handlers import APIHandler, IPythonHandler
from notebook.utils import url_path_join as ujoin
from notebook.utils import path2url
from tornado import web

# attempt to use LibYaml if available
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

if nb_version_info < (5, 2, 0):
    from notebook.base.handlers import json_errors
else:
    # for notebook >= 5.2.0, instead of using json_errors, we must subclass
    # APIHandler. Since we already do this, just do nothing extra
    def json_errors(method):
        return method

__version__ = '0.6.1'

absolute_url_re = re.compile(r'^(f|ht)tps?://')


def _process_nbextension_spec(spec, relative_url_base=''):
    """
    Sanity-check and preprocess a spec loaded from a yaml descriptor file.

    Returns *either* a processed dict *or* a string error message describing
    why the spec was not suitable.
    """
    if not isinstance(spec, dict):
        return 'spec is not a dict, but an instance of {}'.format(type(spec))
    if 'Type' not in spec:
        return 'spec has no Type key'
    valid_types = {'IPython Notebook Extension', 'Jupyter Notebook Extension'}
    if str(spec['Type']).strip() not in valid_types:
        return 'spec has invalid value for Type key: {!r}'.format(spec['Type'])
    if 'Main' not in spec and 'require' not in spec:
        return 'spec has neither "Main" nor "require" key'
    # strip .js file extension from Main to give require path
    if 'require' not in spec:
        spec['require'] = os.path.splitext(spec['Main'])[0]

    spec.setdefault('Name', spec['require'])
    spec.setdefault('Compatibility', '?.x')
    spec.setdefault('Section', 'notebook')

    # generate relative URLs within the nbextensions namespace,
    # from urls relative to the yaml file
    for from_key, to_key in {
            'Link': 'readme', 'Icon': 'icon', 'Main': 'require'}.items():
        # check for the to_key first, use from_key as backup
        # str needed in python 3, otherwise it ends up bytes
        from_val = str(spec.get(to_key, ''))
        if not from_val:
            from_val = str(spec.get(from_key, ''))
        if not from_val:
            continue
        if absolute_url_re.match(from_val):
            spec[to_key] = from_val
        else:
            spec[to_key] = posixpath.normpath(
                ujoin(relative_url_base, from_val))
    return spec


def get_configurable_nbextensions(
        nbextension_dirs, exclude_dirs=('mathjax',), as_dict=False, log=None):
    """Build a list of configurable nbextensions based on YAML descriptor files.

    descriptor files must:
      - be located under one of nbextension_dirs
      - have the file extension '.yaml' or '.yml'
      - contain (at minimum) the following keys:
        - Type: must be 'IPython Notebook Extension' or
                'Jupyter Notebook Extension'
        - Main: relative url of the nbextension's main javascript file
    """
    extension_dict = {}

    # Traverse through nbextension subdirectories to find all yaml files
    # However, don't check directories twice. See
    #   github.com/Jupyter-contrib/jupyter_nbextensions_configurator/issues/25
    already_checked = set()
    for root_nbext_dir in nbextension_dirs:
        if root_nbext_dir in already_checked:
            continue
        else:
            already_checked.add(root_nbext_dir)
        if log:
            log.debug(
                'Looking for nbextension yaml descriptor files in {}'.format(
                    root_nbext_dir))
        for direct, dirs, files in os.walk(root_nbext_dir, followlinks=True):
            # filter to exclude directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for filename in files:
                if os.path.splitext(filename)[1] not in ['.yml', '.yaml']:
                    continue
                yaml_path = os.path.join(direct, filename)
                yaml_relpath = os.path.relpath(yaml_path, root_nbext_dir)
                with io.open(yaml_path, 'r', encoding='utf-8') as stream:
                    try:
                        extension = yaml.load(stream, Loader=SafeLoader)
                    except yaml.YAMLError:
                        if log:
                            log.warning(
                                'Failed to load yaml file {}'.format(
                                    yaml_relpath))
                        continue
                extension = _process_nbextension_spec(
                    extension,
                    relative_url_base=path2url(os.path.dirname(yaml_relpath)))
                if not isinstance(extension, dict):
                    continue
                require = extension['require']

                if log:
                    if require in extension_dict:
                        msg = 'nbextension {!r} has duplicate listings'.format(
                            extension['require'])
                        msg += ' in both {!r} and {!r}'.format(
                            yaml_path, extension_dict[require]['yaml_path'])
                        log.warning(msg)
                        extension['duplicate'] = True
                    else:
                        log.debug('Found nbextension {!r} in {}'.format(
                            extension['Name'], yaml_relpath))

                extension_dict[require] = {
                    'yaml_path': yaml_path, 'extension': extension}
    if as_dict:
        return extension_dict
    return [val['extension'] for val in extension_dict.values()]


class ConfiguratorLogger(logging.LoggerAdapter):
    """Logging adapter to prepend the serverextension name to log messages."""

    def __init__(self, logger):
        super(ConfiguratorLogger, self).__init__(logger, {})

    def process(self, msg, kwargs):
        return '[{}] {}'.format(__name__, msg), kwargs


class NBExtensionHandlerJSON(APIHandler):
    """
    Returns a json list describing the configurable nbextensions.

    Based on part of notebook.services.config.handlers.ConfigHandler
    """

    @APIHandler.log.getter
    def log(self):
        return ConfiguratorLogger(super(NBExtensionHandlerJSON, self).log)

    @web.authenticated
    @json_errors
    def get(self):
        self.set_header("Content-Type", 'application/json')
        nbapp_webapp = self.application
        nbextension_dirs = nbapp_webapp.settings['nbextensions_path']
        extension_list = get_configurable_nbextensions(
            nbextension_dirs=nbextension_dirs, log=self.log)
        self.finish(json.dumps(extension_list))


class NBExtensionHandlerPage(IPythonHandler):
    """Renders the nbextension configuration interface."""

    @IPythonHandler.log.getter
    def log(self):
        return ConfiguratorLogger(super(NBExtensionHandlerPage, self).log)

    @web.authenticated
    def get(self):
        """Render the nbextension configuration interface."""
        self.finish(self.render_template(
            'nbextensions_configurator.html',
            page_title='Nbextensions Configuration',
            **self.application.settings
        ))


class RenderExtensionHandler(IPythonHandler):
    """Renders markdown files as pages."""

    @IPythonHandler.log.getter
    def log(self):
        return ConfiguratorLogger(super(RenderExtensionHandler, self).log)

    @web.authenticated
    def get(self, path):
        """Render given markdown file."""
        if not path.endswith('.md'):
            # for all non-markdown items, we redirect to the actual file
            return self.redirect(self.base_url + path)
        self.finish(self.render_template(
            'rendermd.html',
            md_url=path,
            page_title=path,
            **self.application.settings
        ))


def load_jupyter_server_extension(nbapp):
    """Load and initialise the server extension."""
    logger = ConfiguratorLogger(nbapp.log)
    logger.debug('Loading {}'.format(__version__))
    webapp = nbapp.web_app

    # ensure our template gets into search path
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    logger.debug('  Editing templates path to add {}'.format(templates_dir))
    rootloader = webapp.settings['jinja2_env'].loader
    for loader in getattr(rootloader, 'loaders', [rootloader]):
        if hasattr(loader, 'searchpath') and \
                templates_dir not in loader.searchpath:
            loader.searchpath.append(templates_dir)

    base_url = webapp.settings['base_url']

    # make sure our static files are available
    static_files_path = os.path.normpath(os.path.join(
        os.path.dirname(__file__), 'static'))
    logger.debug(
        '  Editing nbextensions path to add {}'.format(static_files_path))
    if webapp.settings.get('nbextensions_path', None) and static_files_path not in webapp.settings.get('nbextensions_path', []):
        webapp.settings['nbextensions_path'].append(static_files_path)
    if webapp.settings.get('static_path', None) and static_files_path not in webapp.settings.get('static_path', []):
        webapp.settings['static_path'].append(static_files_path)

    # add our new custom handlers
    logger.debug('  Adding new handlers')
    new_handlers = [(ujoin(base_url, '/nbextensions/' + u), h) for u, h in [
        (r"?", NBExtensionHandlerPage),
        (r"nbextensions_configurator/list$", NBExtensionHandlerJSON),
        (r"nbextensions_configurator/rendermd/(.*)", RenderExtensionHandler),
    ]]
    webapp.add_handlers(".*$", new_handlers)

    logger.info('enabled {}'.format(__version__))

def _jupyter_nbextension_paths():
    return [
        dict(
            section="notebook",
            src="static/nbextensions_configurator",
            dest="nbextensions_configurator",
            require='nbextensions_configurator/config_menu/main',
        ),
        dict(
            section="tree",
            src="static/nbextensions_configurator",
            dest="nbextensions_configurator",
            require='nbextensions_configurator/tree_tab/main',
        ),
    ]

def _jupyter_server_extension_paths():
    return [{
        'module': __name__
    }]
