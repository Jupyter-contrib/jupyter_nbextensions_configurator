# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import io
import logging
import os
import random
import shutil

import nose.tools as nt
import yaml
from ipython_genutils.tempdir import TemporaryDirectory
from notebook.utils import url_path_join
from notebook.nbextensions import install_nbextension

import jupyter_nbextensions_configurator
from nbextensions_test_base import (
    get_wrapped_logger, SeleniumNbextensionTestBase,
)

# from http://nose.readthedocs.io/en/latest/writing_tests.html#writing-tests
#
# > nose runs functional tests in the order in which they appear in the module
# > file. TestCase-derived tests and other test classes are run in alphabetical
# > order
#
# So, I name test methods of classes using numbers to control execution order.


class ConfiguratorTest(SeleniumNbextensionTestBase):
    """Tests for the nbextensions_configurator server extension."""

    @classmethod
    def pre_server_setup(cls):
        """Setup a temporary environment in which to run a notebook server."""
        super(ConfiguratorTest, cls).pre_server_setup()
        cls.add_dodgy_yaml_files()
        cls.install_nbexts()
        cls.nbext_configurator_url = url_path_join(
            cls.base_url(), 'nbextensions')

    def test_00_load_nbextensions_page(self):
        """Check that <base_url>/nbextensions url loads correctly."""
        self.driver.get(self.nbext_configurator_url)

    def test_01_page_title(self):
        nt.assert_in('extension', self.driver.title.lower())
        nt.assert_in('configuration', self.driver.title.lower())

    def test_02_body_data_attribute(self):
        nbext_list = self.driver.execute_script('return window.extension_list')
        nt.assert_is_instance(nbext_list, list)
        nt.assert_greater(
            len(nbext_list), 0, 'some nbextensions should be found')

    def test_03_extension_ui_presence(self):
        self.wait_for_selector('.nbext-row', 'an extension ui should load')
        enable_links = self.driver.find_elements_by_css_selector(
            '.nbext-selector')
        nt.assert_greater(
            len(enable_links), 0, 'some nbextensions should have enable links')

    def test_04_readme_rendering(self):
        # load the collapsible headings UI, as it has a readme to render
        collapsible_link = self.driver.find_element_by_partial_link_text(
            'Scratchpad')
        collapsible_link.click()

        # # uncomment below to scroll readme into view
        # # (may require a time.sleep as well)
        # driver.execute_script(
        #     "document.querySelector('.nbext-readme').scrollIntoView()")
        self.wait_for_selector('.nbext-readme-contents img',
                               'there should be an image in the readme')

    def test_05_click_page_readme_link(self):
        self.driver.find_element_by_css_selector('.nbext-page-title a').click()
        self.wait_for_selector('.rendermd-page-title')

    @classmethod
    def install_nbexts(cls):
        nbext_path = url_path_join(
            'https://github.com/minrk/nbextension-scratchpad',
            'archive', 'master.zip')
        inst_funcname = '.'.join([
            install_nbextension.__module__, install_nbextension.__name__])
        logger = get_wrapped_logger(
            name=inst_funcname, log_level=logging.DEBUG)
        install_nbextension(nbext_path, user=True, logger=logger)

    @classmethod
    def add_dodgy_yaml_files(cls):
        """Add in dodgy yaml files in an extra nbextensions dir."""
        dodgy_nbext_dir = cls.dodgy_nbext_dir = TemporaryDirectory()
        dodgy_nbext_dir_path = os.path.join(
            dodgy_nbext_dir.name, 'dodgy_nbextensions')
        os.mkdir(dodgy_nbext_dir_path)
        cls.config.NotebookApp.setdefault(
            'extra_nbextensions_path', []).append(dodgy_nbext_dir_path)

        # an invlaid yaml file
        yaml_path_invalid = os.path.join(
            dodgy_nbext_dir_path, 'nbext_invalid_yaml.yaml')
        with io.open(yaml_path_invalid, 'w') as f:
            f.write('not valid yaml!: [')

        # a yaml file which isn't a dict
        dodgy_yamls = {
            'not_an_nbext': ['valid yaml', "doesn't always",
                             'make for a valid nbext yaml, right?', 3423509],
            'missing_key': {'Main': True},
            'invalid_type': {'Main': 'main.js', 'Type': 'blahblahblah'}
        }
        for fname, yaml_obj in dodgy_yamls.items():
            yaml_path = os.path.join(dodgy_nbext_dir_path, fname + '.yaml')
            with io.open(yaml_path, 'w') as f:
                yaml.dump(yaml_obj, f)

        # a yaml file which shadows an existing extension.
        nbdir = os.path.join(
            os.path.dirname(jupyter_nbextensions_configurator.__file__),
            'static')
        nbexts = (
            jupyter_nbextensions_configurator.get_configurable_nbextensions(
                [nbdir], as_dict=True))
        src = random.choice(list(nbexts.values()))['yaml_path']
        dst = os.path.join(
            dodgy_nbext_dir_path, os.path.relpath(src, start=nbdir))
        dst_dir = os.path.dirname(dst)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        shutil.copy(src, dst)
