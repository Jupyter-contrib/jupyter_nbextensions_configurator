# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import logging
import os
import pipes
import sys
import threading
import time
from subprocess import PIPE, STDOUT, Popen

from jupyter_contrib_core.testing_utils import get_logger
from nose.plugins.skip import SkipTest
from selenium.webdriver.support.ui import WebDriverWait
from tornado import gen
from tornado.ioloop import IOLoop
from traitlets import default
from traitlets.config.application import LevelFormatter

from nbextensions_test_base import get_wrapped_logger, wrap_logger_handlers
from test_nbextensions_configurator import ConfiguratorTest

# run some basic checks to see if jupyterhub is supported on this platform
if os.name in ('nt', 'dos'):
    raise SkipTest('jupyterhub is not supported on Windows.')
elif sys.version_info[:2] < (3, 3):
    raise SkipTest('jupyterhub requires Python version 3.3 or above.')
else:
    try:
        import jupyterhub  # noqa
    except ImportError:
        raise SkipTest(
            'could not import jupyterhub, so skipping jupyterhub tests')
    from jupyterhub.auth import Authenticator
    from jupyterhub.spawner import LocalProcessSpawner
    from jupyterhub.tests.mocking import MockHub, public_url
    from jupyterhub.utils import random_port


class TestSpawner(LocalProcessSpawner):
    """Mock spawner, skipping user-switching that'd need root permissions."""

    @default('log')
    def _log_default(self):
        """wrap loggers for this application."""
        return wrap_logger_handlers(LocalProcessSpawner._log_default(self))

    def make_preexec_fn(self, *a, **kw):
        # skip the setuid stuff
        return

    def user_env(self, env):
        # copy select environment variables.
        env['USER'] = self.user.name
        env.update({k: v for k, v in dict(os.environ).items() if k in [
            'JUPYTER_CONFIG_DIR', 'JUPYTER_DATA_DIR', 'JUPYTER_RUNTIME_DIR',
            'HOME', 'SHELL',
        ]})
        return env

    @gen.coroutine
    def start(self):
        """Start the process. Overridden in order to capture output."""
        self.port = random_port()

        env = self.get_env()
        cmd = []
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        self.log.info("Spawning %s", ' '.join(pipes.quote(s) for s in cmd))
        self.proc = Popen(
            cmd, env=env, preexec_fn=self.make_preexec_fn(self.user.name),
            start_new_session=True,  # don't forward signals
            stdout=PIPE, stderr=STDOUT,
        )
        self.pid = self.proc.pid
        self._read_proc_stderr_thread = thrd = threading.Thread(
            target=self._read_proc_stderr, name='_read_proc_stderr')
        thrd.daemon = True
        thrd.start()
        return (self.ip or '127.0.0.1', self.port)

    def _read_proc_stderr(self):
        logr = get_logger(self.user.name)
        logr.handlers[0].setFormatter(logging.Formatter(fmt='    %(message)s'))
        logr = wrap_logger_handlers(logr)
        for line in iter(self.proc.stdout.readline, b''):
            logr.info(line.decode('utf-8').strip('\n'))


TestSpawner.debug.default_value = True


class MockAuthenticator(Authenticator):
    """
    Dummy authentication. Returns the username if login is successful.

    Returns None otherwise.
    """

    _default_whitelist = {'nandy', 'aela'}

    @default('log')
    def _log_default(self):
        """wrap loggers for this application."""
        return wrap_logger_handlers(Authenticator._log_default(self))

    @gen.coroutine
    def authenticate(self, handler, data):
        username, password = data['username'], data['password']
        # just use equality for testing
        return (username if password == username else None)

    @default('whitelist')
    def get_default_whitelist(self):
        return self._default_whitelist


class JupyterHubConfiguratorTest(ConfiguratorTest):
    """Base class for nbextensions test cases running through jupyterhub."""

    uses_jupyterhub = True  # attribute used for filtering nose tests

    # we can't patch jupyter paths for single-user server running in a
    # subprocess, but we can patch environment variables passed to the
    # subprocess, so do a user install, to take advantage of the $HOME variable
    _install_user = True

    @classmethod
    def base_url(cls):
        return public_url(cls.app, cls.user)

    @classmethod
    def setup_class(cls):
        cls._failure_occurred = False  # flag for logging
        cls.log = get_wrapped_logger(cls.__name__)
        cls.log.handlers[0].setFormatter(LevelFormatter(
            fmt=(
                '[%(levelname)1.1s '
                '%(asctime)s.%(msecs).03d '
                '%(name)s %(module)s:%(lineno)d]'
                '%(message)s'
            ),
            datefmt='%H:%M:%S',
        ))
        cls._setup_patches()
        cls.pre_server_setup()

        cls.log.info('starting webdriver')
        cls.init_webdriver()
        cls.log.info('Starting jupyterhub server app thread')
        cls.app = MockHub.instance(
            log_datefmt="%H:%M:%S",
            authenticator_class=MockAuthenticator,
            spawner_class=TestSpawner,
        )
        # need to start jupyterhub app before calling super, as the super will
        # wait for the page to load
        try:
            cls.app.log = wrap_logger_handlers(cls.app.log)
            cls.app.start([])
        except Exception:
            cls._server_cleanup(
                error_msg='failed to start jupyterhub app')
            raise

        try:
            cls.log.info(
                'Logging into hub-spawned single-user notebook server.')
            login_url = public_url(cls.app) + 'login'
            cls.driver.get(login_url)
            cls.uname = name = next(iter(MockAuthenticator._default_whitelist))
            cls.wait_for_selector('#username_input').send_keys(name)
            cls.wait_for_selector('#password_input').send_keys(name)
            # This short wait seems necessary to avoid http 503 error
            time.sleep(1)
            cls.wait_for_selector('#login_submit').click()
            # wait for redirect to single-user server
            WebDriverWait(cls.driver, 30).until(
                lambda driver:
                    cls.app.users[name] is not None and
                    cls.app.users[name].server is not None and
                    cls.driver.current_url.startswith(
                        public_url(cls.app, cls.app.users[name])))
            # wait till single-user page loaded
            cls.wait_for_selector('#tab_content', timeout=10)

            user = cls.user = cls.app.users[name]
            if not user.running:
                io_loop = IOLoop()
                io_loop.make_current()
                io_loop.run_sync(user.spawn)
        except Exception:
            cls._server_cleanup(
                error_msg='failed to start/login to single-user server')
            raise

    @classmethod
    def _server_cleanup(cls, error_msg=None):
        if error_msg is not None:
            cls._failure_occurred = True
            cls.log.error(error_msg)
        cls.app.stop()
        # do cleanup explicitly as it's only registered using atexit
        cls.app.cleanup()

    @classmethod
    def teardown_class(cls):
        try:
            cls._server_cleanup()
            cls.app.__class__.clear_instance()
        finally:
            try:
                for ptch in cls.jupyter_patches:
                    ptch.stop()
            finally:
                try:
                    for func in cls.removal_funcs:
                        func()
                finally:
                    cls._print_logs_on_failure()
