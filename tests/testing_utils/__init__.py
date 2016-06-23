# -*- coding: utf-8 -*-
"""Test utilities."""

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import logging
import os
import sys
from threading import RLock

from traitlets.config.application import LevelFormatter
from traitlets.traitlets import default


def stringify_env(env):
    """
    Convert environment vars dict to str: str (not unicode) for py2 on Windows.

    Python 2 on Windows doesn't handle Unicode objects in environment, even if
    they can be converted to ASCII string, which can cause problems for
    subprocess calls in modules importing unicode_literals from future.
    """
    if sys.version_info[0] < 3 and os.name == 'nt':
        return {str(key): str(val) for key, val in env.iteritems()}
    return env


class GlobalMemoryHandler(logging.Handler):
    """
    A MemoryHandler which uses a single buffer across all instances.

    In addition, will only flush logs when explicitly called to.
    """

    _buffer = None  # used as a class-wide attribute
    _lock = None  # used as a class-wide attribute

    @classmethod
    def _setup_class(cls):
        if cls._lock is None:
            cls._lock = RLock()
        if cls._buffer is None:
            with cls._lock:
                cls._buffer = []

    def __init__(self, target):
        logging.Handler.__init__(self)
        self.target = target
        self._setup_class()

    def emit(self, record):
        """
        Emit a record.

        Append the record and its target to the buffer.
        Don't check shouldFlush like regular MemoryHandler does.
        """
        self.__class__._buffer.append((record, self.target))

    @classmethod
    def flush_to_target(cls):
        """
        Sending the buffered records to their respective targets.

        The class-wide record buffer is also cleared by this operation.
        """
        with cls._lock:
            for record, target in cls._buffer:
                target.handle(record)
            cls.clear_buffer()

    @classmethod
    def clear_buffer(cls):
        with cls._lock:
            cls._buffer = []

    @classmethod
    def rotate_buffer(cls, num_places=1):
        with cls._lock:
            cls._buffer = cls._buffer[-num_places:] + cls._buffer[:-num_places]

    def close(self):
        """Close the handler."""
        try:
            self.flush()
        finally:
            logging.Handler.close(self)


def wrap_logger_handlers(logger):
    """Wrap a logging handler in a GlobalMemoryHandler."""
    # clear original log handlers, saving a copy
    handlers_to_wrap = logger.handlers
    logger.handlers = []
    # wrap each one
    for handler in handlers_to_wrap:
        if isinstance(handler, GlobalMemoryHandler):
            wrapping_handler = handler
        else:
            wrapping_handler = GlobalMemoryHandler(target=handler)
        logger.addHandler(wrapping_handler)
    return logger


def get_logger(name=__name__, log_level=logging.DEBUG):
    """
    Return a logger with a default StreamHandler.

    Adapted from
        tratilets.config.application.Application._log_default
    """
    log = logging.getLogger(name)
    log.setLevel(log_level)
    log.propagate = False
    _log = log  # copied from Logger.hasHandlers() (new in Python 3.2)
    while _log:
        if _log.handlers:
            return log
        if not _log.propagate:
            break
        else:
            _log = _log.parent
    if sys.executable.endswith('pythonw.exe'):
        # this should really go to a file, but file-logging is only
        # hooked up in parallel applications
        _log_handler = logging.StreamHandler(open(os.devnull, 'w'))
    else:
        _log_handler = logging.StreamHandler()
    _log_formatter = LevelFormatter(
        fmt='[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s] %(message)s',
        datefmt='%H:%M:%S')
    _log_handler.setFormatter(_log_formatter)
    log.addHandler(_log_handler)
    return log


def get_wrapped_logger(*args, **kwargs):
    """Return a logger with StreamHandler wrapped in a GlobalMemoryHandler."""
    return wrap_logger_handlers(get_logger(*args, **kwargs))


def patch_traitlets_app_logs(klass):
    """
    Patch an App's default log method for use in nose tests.

    This is for use on subclasses of tratilets.config.application.Application
    and essentially removes handlers from the default logger, then sets it to
    propagate so that nose can capture the logs.
    """
    @default('log')
    def new_default_log(self):
        logger = super(klass, self)._log_default()
        # clear log handlers and propagate to root for nose to capture
        logger.propagate = True
        logger.handlers = []
        return logger
    klass._log_default = new_default_log
