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
from jupyter_contrib_core.notebook_compat.nbextensions import _get_config_dir
from notebook.services.config import ConfigManager
from notebook.utils import url_path_join
from selenium.common.exceptions import NoSuchElementException

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

    @property
    def nbext_configurator_url(self):
        return url_path_join(self.base_url(), 'nbextensions')

    @classmethod
    def pre_server_setup(cls):
        """Setup a temporary environment in which to run a notebook server."""
        super(ConfiguratorTest, cls).pre_server_setup()
        cls.add_dodgy_yaml_files()

    def test_00_load_nbextensions_page(self):
        """Check that <base_url>/nbextensions url loads correctly."""
        self.driver.get(self.nbext_configurator_url)

    def test_01_page_title(self):
        nt.assert_in('extension', self.driver.title.lower())
        nt.assert_in('configuration', self.driver.title.lower())

    def test_02_body_data_attribute(self):
        nbext_list = self.driver.execute_script('return window.extension_list')
        # we no longer embed the list into the page
        nt.assert_is_none(nbext_list)

    def test_03_extension_ui_presence(self):
        self.wait_for_selector(
            '.nbext-ext-row', 'an nbextension ui should load')
        enable_links = self.driver.find_elements_by_css_selector(
            '.nbext-selector')
        nt.assert_greater(
            len(enable_links), 0, 'some nbextensions should have enable links')

    def test_04_readme_rendering(self):
        # load an nbextension UI whose readme contains an image to render
        self.wait_for_partial_link_text('dashboard').click()
        self.wait_for_selector('.nbext-readme > .panel-body img',
                               'there should be an image in the readme')

    def test_05_click_page_readme_link(self):
        self.driver.find_element_by_css_selector('.nbext-page-title a').click()
        self.wait_for_selector('#render-container img',
                               'there should be an image in the readme')

    def test_06_enable_tree_tab(self):
        self.driver.get(self.nbext_configurator_url)
        self.wait_for_selector(
            '.nbext-ext-row', 'an nbextension ui should load')
        # now enable the appropriate nbextension
        self.wait_for_partial_link_text(
            'dashboard'
        ).find_element_by_css_selector('.nbext-enable-toggle').click()
        self.check_extension_enabled(
            'tree', 'nbextensions_configurator/tree_tab/main',
            expected_status=True)

    def test_07_open_tree_tab(self):
        self.driver.get(self.base_url())
        self.wait_for_selector(
            '#tabs a[href$=nbextensions_configurator]').click()
        self.wait_for_selector(
            '.nbext-ext-row', 'an nbextension ui should load')

    def test_08_disable_tree_tab(self):
        # now disable the appropriate nbextension & wait for update to config
        self.wait_for_partial_link_text(
            'dashboard'
        ).find_element_by_css_selector('.nbext-enable-toggle').click()
        self.check_extension_enabled(
            'tree', 'nbextensions_configurator/tree_tab/main',
            expected_status=False)
        self.driver.get(self.base_url())
        with nt.assert_raises(AssertionError):
            self.wait_for_selector('#tabs a[href$=nbextensions_configurator]')

    def test_09_no_unconfigurable_yet(self):
        self.driver.get(self.nbext_configurator_url)
        self.wait_for_selector(
            '.nbext-ext-row', 'an nbextension ui should load')
        selector = self.driver.find_element_by_css_selector('.nbext-selector')
        nt.assert_not_in(
            'daemon', selector.text,
            'There should be no daemons in the selector yet')

    def test_10_refresh_list(self):
        # 'enable' a fake nbextension
        section, require = 'notebook', 'balrog/daemon'
        self.set_extension_enabled(section, require, True)
        # refresh the list to check that it appears
        self.wait_for_selector('.nbext-button-refreshlist').click()
        self.wait_for_partial_link_text(require)
        selector = self.driver.find_element_by_css_selector('.nbext-selector')
        nt.assert_in(
            'daemon', selector.text,
            'There should now be a daemon in the selector')

    def test_11_allow_configuring_incompatibles(self):
        require = 'balrog/daemon'
        # allow configuring incompatibles
        self.wait_for_selector(
            '#nbext_hide_incompat',
            'potentially incompatible nbextensions should show checkbox'
        ).click()
        # select it, now it's configurable
        self.driver.find_element_by_partial_link_text(require).click()

    def test_12_unconfigurable(self):
        section, require = 'notebook', 'balrog/daemon'
        sel_disable = '.nbext-enable-btns .btn:nth-child(2)'
        sel_forget = '.nbext-enable-btns .btn:nth-child(3)'
        # wait for ui to load
        self.wait_for_xpath('//h3[contains(text(), "daemon")]')
        # wait a second for the other nbextension ui to hide
        time.sleep(1)
        # there should be no forget button visible yet
        with nt.assert_raises(NoSuchElementException):
            self.driver.find_element_by_css_selector(sel_forget)
        # disable balrog
        self.wait_for_selector(sel_disable)
        visible_disablers = [
            el for el in self.driver.find_elements_by_css_selector(sel_disable)
            if el.is_displayed()]
        nt.assert_equal(1, len(visible_disablers),
                        'Only one disable button should be visible')
        visible_disablers[0].click()
        # now forget it
        self.wait_for_selector(sel_forget, 'A forget button should display')
        self.driver.find_element_by_css_selector(sel_forget).click()
        # confirm dialog
        self.wait_for_selector(
            '.modal-dialog .modal-footer .btn-danger',
            'a confirmation dialog should show'
        ).click()
        # it should no longer be enabled in config
        time.sleep(1)
        conf = self.get_config_manager().get(section)
        stat = conf.get('load_extensions', {}).get(require)
        nt.assert_is_none(
            stat, '{} should not have a load_extensions entry'.format(require))
        # and should no longer show in the list
        self.wait_for_selector(
            '.nbext-selector nav ul li', 'some nbextensions should show')
        nbext_sel = self.driver.find_element_by_css_selector('.nbext-selector')
        nt.assert_not_in(
            'daemon', nbext_sel.text,
            'There should no longer be a daemon in the selector')

    @classmethod
    def get_config_manager(cls):
        try:
            # single-user notebook server tests use cls.notebook for app
            return cls.notebook.config_manager
        except AttributeError:
            # jupyterhub-based tests don't (can't) have cls.notebook defined,
            # so we must construct a ConfigManager from scratch
            return ConfigManager(
                log=cls.log,
                config_dir=os.path.join(_get_config_dir(user=True), 'nbconfig')
            )

    @classmethod
    def set_extension_enabled(cls, section, require, enabled):
        cm = cls.get_config_manager()
        new_conf = {}
        if enabled is not None:
            enabled = bool(enabled)
        new_conf.setdefault('load_extensions', {})[require] = enabled
        cm.update(section, new_conf)

    @classmethod
    def check_extension_enabled(cls, section, require, expected_status=True,
                                timeout=10, check_period=0.5):
        cm = cls.get_config_manager()
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
                        '' if expected_status else 'not '))

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

        # a yaml file which shadows an existing nbextension.
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
