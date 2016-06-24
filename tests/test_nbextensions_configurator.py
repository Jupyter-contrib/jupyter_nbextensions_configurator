# -*- coding: utf-8 -*-

from __future__ import (
    absolute_import, division, print_function, unicode_literals,
)

import io
import os
import random
import shutil
import time

import nose.tools as nt
import yaml
from notebook.utils import url_path_join

import jupyter_nbextensions_configurator
from nbextensions_test_base import SeleniumNbextensionTestBase

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
        # load an extension UI which has a readme containing an image to render
        partial_txt = 'dashboard'
        self.wait_for_partial_link_text(partial_txt)
        sel_link = self.driver.find_element_by_partial_link_text(partial_txt)
        sel_link.click()
        self.wait_for_selector('.nbext-readme-contents img',
                               'there should be an image in the readme')

    def test_05_click_page_readme_link(self):
        self.driver.find_element_by_css_selector('.nbext-page-title a').click()
        self.wait_for_selector('#render-container img',
                               'there should be an image in the readme')

    def test_06_enable_tree_tab(self):
        self.driver.get(self.nbext_configurator_url)
        self.wait_for_selector('.nbext-row', 'an extension ui should load')
        # now enable the appropriate nbextension
        partial_txt = 'dashboard'
        self.wait_for_partial_link_text(partial_txt)
        sel_link = self.driver.find_element_by_partial_link_text(partial_txt)
        sel_link.find_element_by_css_selector('.nbext-enable-toggle').click()
        self.check_extension_enabled(
            'tree', 'nbextensions_configurator/tree_tab/main',
            expected_status=True)

    def test_07_open_tree_tab(self):
        self.driver.get(self.base_url())
        tab_selector = '#tabs a[href$=nbextensions_configurator]'
        self.wait_for_selector(tab_selector)
        self.driver.find_element_by_css_selector(tab_selector).click()
        self.wait_for_selector('.nbext-row', 'an extension ui should load')

    def test_08_disable_tree_tab(self):
        # now disable the appropriate nbextension & wait for update to config
        partial_txt = 'dashboard'
        self.wait_for_partial_link_text(partial_txt)
        sel_link = self.driver.find_element_by_partial_link_text(partial_txt)
        sel_link.find_element_by_css_selector('.nbext-enable-toggle').click()
        self.check_extension_enabled(
            'tree', 'nbextensions_configurator/tree_tab/main',
            expected_status=False)

    @classmethod
    def check_extension_enabled(cls, section, require, expected_status=True,
                                timeout=10, check_period=0.5):
        cm = cls.notebook.config_manager
        for ii in range(0, max(1, int(timeout / check_period))):
            load_exts = cm.get(section).get('load_extensions', {})
            enabled = [req for req, en in load_exts.items() if en]
            if (require in enabled) == expected_status:
                break
            time.sleep(check_period)
        assert_func = (
            nt.assert_in if expected_status else nt.assert_not_in)
        assert_func(require, enabled,
                    'nbxtension should {}be in enabled list'.format(
                        '' if expected_status else ' not'))

    @classmethod
    def add_dodgy_yaml_files(cls):
        """Add in dodgy yaml files in an extra nbextensions dir."""
        cls.jupyter_dirs['dodgy'] = {
            'nbexts': os.path.join(cls.jupyter_dirs['root'], 'dodgy', 'nbext')}
        dodgy_nbext_dir_path = cls.jupyter_dirs['dodgy']['nbexts']
        os.makedirs(dodgy_nbext_dir_path)
        cls.config.NotebookApp.setdefault(
            'extra_nbextensions_path', []).append(dodgy_nbext_dir_path)

        # an invalid yaml file
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
