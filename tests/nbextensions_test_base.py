# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import logging
import os
from threading import Event, Thread

import jupyter_core.paths
from ipython_genutils.tempdir import TemporaryDirectory
from nose.plugins.attrib import attr as nose_attr
from nose.plugins.skip import SkipTest
from notebook.notebookapp import NotebookApp
from notebook.tests.launchnotebook import NotebookTestBase
from tornado.ioloop import IOLoop
from traitlets.config import Config
from traitlets.traitlets import default

from jupyter_nbextensions_configurator.notebook_compat import serverextensions
from testing_utils import (
    GlobalMemoryHandler, get_wrapped_logger, stringify_env,
    wrap_logger_handlers,
)

try:
    from unittest.mock import patch  # py3
except ImportError:
    from mock import patch  # py2

no_selenium = True
try:
    from selenium import webdriver
except ImportError:
    pass
else:
    no_selenium = False
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.support.ui import WebDriverWait


class NoseyNotebookApp(NotebookApp):
    """Wrap the regular logging handler(s). for use inside nose tests."""

    @default('log')
    def _log_default(self):
        """wrap loggers for this application."""
        return wrap_logger_handlers(NotebookApp._log_default(self))


class NbextensionTestBase(NotebookTestBase):
    """
    Base class for nbextensions test case classes.

    We override the setup_class method from NotebookTestBase in order to
    install things, and also to set log_level to debug.
    Also split some of the setup_class method into separate methods in order to
    simplify subclassing.
    """
    config = Config(NotebookApp={'log_level': logging.DEBUG})

    # these are added for notebook < 4.1, where url_prefix wasn't defined.
    # However, due to the fact that the base_url body data attribute in the
    # page template isn't passed through the urlencode jinja2 filter,
    # so we can't expect base_url which would need encoding to work :(
    if not hasattr(NotebookTestBase, 'url_prefix'):
        url_prefix = '/ab/'

        @classmethod
        def base_url(cls):
            return 'http://localhost:%i%s' % (cls.port, cls.url_prefix)

    @classmethod
    def pre_server_setup(cls):
        """Setup a temporary environment in which to run a notebook server."""
        cls.config_dir = TemporaryDirectory()
        cls.data_dir = TemporaryDirectory()
        cls.home_dir = TemporaryDirectory()
        cls.notebook_dir = TemporaryDirectory()
        cls.runtime_dir = TemporaryDirectory()

        cls.env_patch = patch.dict('os.environ', stringify_env({
            'HOME': cls.home_dir.name,
            'IPYTHONDIR': os.path.join(cls.home_dir.name, '.ipython'),
            'JUPYTER_DATA_DIR': cls.data_dir.name
        }))
        cls.env_patch.start()

        cls.path_patch = patch.object(
            jupyter_core.paths, 'SYSTEM_JUPYTER_PATH', [])
        cls.path_patch.start()

        # added to install things!
        cls.log.info('Enabling jupyter_nbextensions_configurator')
        inst_func = serverextensions.toggle_serverextension_python
        inst_funcname = '.'.join([inst_func.__module__, inst_func.__name__])
        logger = get_wrapped_logger(
            name=inst_funcname, log_level=logging.DEBUG)
        serverextensions.toggle_serverextension_python(
            'jupyter_nbextensions_configurator', enabled=True, logger=logger)

    @classmethod
    def get_server_kwargs(cls, **overrides):
        kwargs = dict(
            port=cls.port,
            port_retries=0,
            open_browser=False,
            config_dir=cls.config_dir.name,
            data_dir=cls.data_dir.name,
            runtime_dir=cls.runtime_dir.name,
            notebook_dir=cls.notebook_dir.name,
            base_url=cls.url_prefix,
            config=cls.config,
        )
        kwargs.update(overrides)
        return kwargs

    @classmethod
    def start_server_thread(cls, started_event):
        """
        Start a notebook server in a separate thread.

        The start is signalled using the passed Event instance.
        """
        cls.log.info('Starting notebook server app thread')
        app = cls.notebook = NoseyNotebookApp(**cls.get_server_kwargs())
        # don't register signal handler during tests
        app.init_signal = lambda: None
        app.initialize(argv=[])
        loop = IOLoop.current()
        loop.add_callback(started_event.set)
        try:
            app.start()
        finally:
            # set the event, so failure to start doesn't cause a hang
            started_event.set()
            # app.session_manager.close call was added after notebook 4.0
            if hasattr(app.session_manager, 'close'):
                app.session_manager.close()

    @classmethod
    def setup_class(cls):
        """Install things & setup a notebook server in a separate thread."""
        cls.log = get_wrapped_logger(cls.__name__)
        cls.pre_server_setup()
        started = Event()
        cls.notebook_thread = Thread(
            target=cls.start_server_thread, args=[started])
        cls.notebook_thread.start()
        started.wait()
        cls.wait_until_alive()


@nose_attr('js')
class SeleniumNbextensionTestBase(NbextensionTestBase):

    @classmethod
    def setup_class(cls):
        if no_selenium:
            raise SkipTest('Selenium not installed. '
                           'Skipping selenium-based test.')
        if os.environ.get('TRAVIS_OS_NAME') == 'osx':
            raise SkipTest("Don't do selenium tests on travis osx")
        super(SeleniumNbextensionTestBase, cls).setup_class()

        if os.environ.get('CI') and os.environ.get('TRAVIS'):
            cls.log.info('Running in CI environment. Using Sauce.')
            username = os.environ['SAUCE_USERNAME']
            access_key = os.environ['SAUCE_ACCESS_KEY']
            capabilities = {
                # 'platform': 'Mac OS X 10.9',
                'platform': 'Linux',
                'browserName': 'firefox',
                'version': 'latest',
                'tags': [os.environ['TOXENV'], 'CI'],
                'name': cls.__name__
            }
            hub_url = 'http://{}:{}@ondemand.saucelabs.com:80/wd/hub'.format(
                username, access_key)
            if os.environ.get('TRAVIS'):
                # see https://docs.travis-ci.com/user/gui-and-headless-browsers
                # and https://docs.travis-ci.com/user/sauce-connect
                capabilities.update({
                    'tunnel-identifier': os.environ['TRAVIS_JOB_NUMBER'],
                    'build': os.environ['TRAVIS_BUILD_NUMBER'],
                })
            cls.driver = webdriver.Remote(
                desired_capabilities=capabilities, command_executor=hub_url)
        else:
            # local test
            cls.driver = webdriver.Firefox()

        cls._failure_occurred = False  # flag for logging

    def run(self, results):
        """Run a given test. Overridden in order to access results."""
        # in py2 unittest, run doesn't return the results object, so we need to
        # create one in order to have a reference to it.
        if results is None:
            results = self.defaultTestResult()
        super(SeleniumNbextensionTestBase, self).run(results)
        if results.failures or results.errors:
            self.__class__._failure_occurred = True
        return results

    @classmethod
    def teardown_class(cls):
        if cls._failure_occurred:
            cls.log.info('\n'.join([
                '',
                '\t\tFailed test!',
                '\t\tCaptured logging:',
            ]))
            GlobalMemoryHandler.rotate_buffer(1)
            GlobalMemoryHandler.flush_to_target()

            cls.log.info('\n\t\tjavascript console logs below...\n\n')
            browser_logger = get_wrapped_logger(
                name=cls.__name__ + '.driver', log_level=logging.DEBUG)
            for entry in cls.driver.get_log('browser'):
                level = logging._nameToLevel.get(entry['level'], logging.ERROR)
                msg = entry['message'].strip()
                browser_logger.log(level, msg)
                record, target = GlobalMemoryHandler._buffer[-1]
                record.ct = entry['timestamp'] / 1000.
                GlobalMemoryHandler._buffer[-1] = record, target
            GlobalMemoryHandler.flush_to_target()

        if (not cls._failure_occurred) or os.environ.get('CI'):
            cls.log.info('closing webdriver')
            cls.driver.quit()
        else:
            cls.log.info('keeping webdriver open')

        super(SeleniumNbextensionTestBase, cls).teardown_class()

    def wait_for_selector(self, css_selector, message='', timeout=5):
        """WebDriverWait for a selector to appear, fail test on timeout."""
        try:
            WebDriverWait(self.driver, 5).until(
                ec.presence_of_element_located((
                    By.CSS_SELECTOR, css_selector)))
        except TimeoutException:
            if message:
                message += '\n'
            self.fail(
                '{}No element matching selector {!r} found in {}s'.format(
                    message, css_selector, timeout))
