Jupyter Nbextensions Configurator
=================================

[![Join the chat at https://gitter.im/jcb91/jupyter_nbextensions_configurator](https://img.shields.io/gitter/room/jcb91/jupyter_nbextensions_configurator.svg?maxAge=3600)](https://gitter.im/jcb91/jupyter_nbextensions_configurator?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)
[![Travis-CI Build Status](https://img.shields.io/travis/jcb91/jupyter_nbextensions_configurator.svg?maxAge=3600&label=Travis%20build)](https://travis-ci.org/jcb91/jupyter_nbextensions_configurator)
[![Appveyor Build status](https://img.shields.io/appveyor/ci/jcb91/jupyter_nbextensions_configurator.svg?maxAge=3600&label=Windows%20build)](https://ci.appveyor.com/project/jcb91/jupyter_nbextensions_configurator)
[![Coveralls python test coverage](https://img.shields.io/coveralls/jcb91/jupyter_nbextensions_configurator/master.svg?maxAge=3600&label=Coveralls%20coverage)](https://coveralls.io/github/jcb91/jupyter_nbextensions_configurator)
[![Codecov python test coverage](https://img.shields.io/codecov/c/github/jcb91/jupyter_nbextensions_configurator/master.svg?maxAge=3600&label=Codecov%20coverage)](https://codecov.io/gh/jcb91/jupyter_nbextensions_configurator)

A server extension for [jupyter notebook](https://github.com/jupyter/notebook)
which provides configuration interfaces for notebook extensions (nbextensions).


The `jupyter_nbextensions_configurator` jupyter server extension provides
graphical user interfaces for configuring which nbextensions are enabled
(load automatically for every notebook), and display their readme files.
In addition, for extensions which include an appropriate yaml descripor file
(see below), the interface also provides controls to configure the extensions'
options.

This project was spun out of work from
[`ipython-contrib/IPython-notebook-extensions`][contrib repo url].

[contrib repo url]: https://github.com/ipython-contrib/IPython-notebook-extensions

Installation
------------

The installation has three steps:

1. Installing the pip package. this should be as simple as
  ```
  pip install jupyter_nbextensions_configurator
  ```

2. Configuring the notebook server to load the server extension.
  For notebook versions >= 4.2.0, you can do this using the jupyter machinery with
  ```
  jupyter serverextension enable jupyter_nbextensions_configurator
  ```
  with whichever flags (such as `--user` for single-user, `--sys-prefix` for
  installations into virtual environments, `--system` for ystem-wide installs,
  etc.) are appropriate for your needs.
  For notebook versions before 4.2.0, you can use the provided shim script
  (which essentially duplicates the jupyter installation machinery for versions
  which don't have it already) with the same possible flags:
  ```
  jupyter_nbextensions_configurator enable
  ```
3. Finally, you'll need to restart the notebook server. Once restarted, you
  should be able to find the configurator user interfaces as described below.


Usage
-----
Once `jupyter_nbextensions_configurator` is installed and enabled, and your
notebook server has been restarted, you should be able to find the nbextensions
configuration interface at the url `<base_url>nbextensions`, where
`<base_url>` is described below (for simple installs, it's usually just `/`, so
the UI is at `/nbextensions`).

![](src/jupyter_nbextensions_configurator/static/nbextensions_configurator/icon.png)

###base_url
For most single-user notebook servers, the dashboard (the file-browser view)
is at

    http://localhost:8888/tree

So the `base_url` is the part between the host (`http://localhost:8888`) and
`tree`, so in this case it's the default value of just `/`.
If you have a non-default base url (such as with JupyterHub), you'll need to
prepend it to the url. So, if your dashboard is at

    http://localhost:8888/custom/base/url/tree


then you'll find the nbextensions configuration page at

    http://localhost:8888/custom/base/url/nbextensions

### tree tab
In addition to the main standalone page, the nbextensions configurator
interface is also available as a tab on the dashboard, once it's been
configured to appear there.
To do this, go to the `/nbextensions` url described above, and enable the
nbextension `Nbextensions dashboard tab`


YAML file format
----------------

You don't need to know about the yaml files in order simply to use
`jupyter_nbextensions_configurator`.
A notebook extension is 'found' by the `jupyter_nbextensions_configurator`
server extension when a special yaml file describing the nbextension and its
options is found in the notebook server's `nbextensions_path`.
The yaml file can have any name with the extension `.yaml` or `.yml`, and
describes the notebook extension and its options to
`jupyter_nbextensions_configurator`.

The case-sensitive keys in the yaml file are as follows:

* **Type**          - (*required*) identifier, must be `IPython Notebook Extension` or `Jupyter Notebook Extension` (case sensitive)
* **Name**          - unique name of the extension
* **Description**   - short explanation of the extension
* **Link**          - a url for more documentation. If this is a relative url with a `.md` extension (recommended!), the markdown readme is rendered on the config page.
* **Icon**          - a url for a small icon for the config page (rendered 120px high, should preferably end up 400px wide. Recall HDPI displays may benefit from a 2x resolution icon).
* **Main**          - (*required*) main javascript file that is loaded, typically `main.js`
* **Compatibility** - Jupyter major version compatibility, e.g. `3.x` or `4.x`, `3.x 4.x`, `3.x, 4.x, 5.x`
* **Parameters**    - Optional list of configuration parameters. Each item is a dictionary with (some of) the following keys:
  * **name**        - (*required*) this is the name used to store the configuration variable in the config json. It follows a json-like structure, so you can use `.` to separate sub-objects e.g. `myextension.buttons_to_add.play`.
  * **description** - description of the configuration parameter
  * **default**     - a default value used to populate the tag on the nbextensions config page if no value is found in config. Note that this is more of a hint to the user than anything functional - since it's only set in the yaml file, the javascript implementing the extension in question might actually use a different default, depending on the implementation.
  * **input_type**  - controls the type of html tag used to render the parameter on the configuration page. Valid values include `text`, `textarea`, `checkbox`, [html5 input tags such as `number`, `url`, `color`, ...], plus a final type of `list`
  * **list_element** - for parameters with input_type `list`, this is used in place of `input_type` to render each element of the list
  * finally, extras such as **min** **step** **max** may be used by `number` tags for validation

Example:

```yaml
Type: IPython Notebook Extension
Name: Limit Output
Description: This extension limits the number of characters that can be printed below a codecell
Link: readme.md
Icon: icon.png
Main: main.js
Compatibility: 4.x
Parameters:
- name: limit_output
  description: Number of characters to limit output to
  input_type: number
  default: 10000
  step: 1
  min: 0
- name: limit_output_message
  description: Message to append when output is limited
  input_type: text
  default: '**OUTPUT MUTED**'
```


Troubleshooting
---------------

If you encounter problems with this config page, you can:
 * check the [issues page][this repo issues] for the [github repository][this repo].
   If you can't find one that fits your problem, please create a new one!
 * ask in the project's [gitter chatroom][gitter url]

For debugging, useful information can (sometimes) be found by:

 * Checking for any error messages in the notebook server output logs
 * Check for error messages in the [JavaScript console][javascript console howto] of the browser.

[this repo]: https://github.com/jcb91/jupyter_nbextensions_configurator
[this repo issues]: https://github.com/jcb91/jupyter_nbextensions_configurator/issues
[javascript console howto]: webmasters.stackexchange.com/questions/8525/how-to-open-the-javascript-console-in-different-browsers

