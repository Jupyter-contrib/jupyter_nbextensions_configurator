define(function (require, exports, module) {
    "use strict";

    var $ = require('jqueryui');
    var Jupyter = require('base/js/namespace');
    var events = require('base/js/events');
    var utils = require('base/js/utils');
    var nbextensions_configurator = require('../main');
    var rendermd = require('../render/render');

    var base_url = utils.get_body_data('baseUrl');
    var api_url = utils.url_path_join(base_url, 'nbextensions/nbextensions_configurator/list');

    function refresh_configurable_extensions_list() {
        return nbextensions_configurator.load_all_configs().then(function () {
            return utils.promising_ajax(api_url, {
                cache: false,
                type: "GET",
                dataType: "json",
            });
        }).then(function (extension_list) {
            nbextensions_configurator.build_extension_list(extension_list);
            $('.nbext-selector li:not(.disabled)').last().children('a').click();
        });
    }

    function insert_tab () {
        var tab_text = 'Nbextensions';
        var tab_id = 'nbextensions_configurator';

        var tab_pane = $('<div/>')
            .attr('id', tab_id)
            .append(nbextensions_configurator.build_configurator_ui())
            .addClass('tab-pane')
            .appendTo('.tab-content');

        var tab_buttons = $('<div/>')
            .addClass('no-padding tree-buttons pull-right')
            .prependTo(tab_pane.find('.nbext-selector'));

        var ext_buttons = $('<span/>')
            .attr('id','nbextensions_configurator_buttons')
            .appendTo(tab_buttons);

        var refresh_button = $('<button/>')
            .attr({
                id: 'refresh_nbextensions_configurator_list',
                title:'Refresh nbextensions list'
            })
            .addClass('btn btn-default btn-xs')
            .appendTo(ext_buttons);

        $('<i/>')
            .addClass('fa fa-refresh')
            .appendTo(refresh_button);

        var tab_link = $('<a>')
            .text(tab_text)
            .attr('href', '#' + tab_id)
            .attr('data-toggle', 'tab')
            .on('click', function (evt) {
                window.history.pushState(null, null, '#' + tab_id);
            });

        $('<li>')
            .append(tab_link)
            .appendTo('#tabs');

    }

    function load_ipython_extension () {
        // add css first
        $('<link>')
            .attr('rel', 'stylesheet')
            .attr('type', 'text/css')
            .attr('href', require.toUrl('../main.css'))
            .appendTo('head');
        // prepare for rendermd usage
        rendermd.add_markdown_css();

        insert_tab();
        refresh_configurable_extensions_list();
    }

    return {
        load_ipython_extension : load_ipython_extension
    };

});