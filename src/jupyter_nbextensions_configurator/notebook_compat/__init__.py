# -*- coding: utf-8 -*-
"""
Shim providing notebook-4.2 compatible extensions stuff for earlier versions.

objects imported from notebook_compat.nbextensions will be
 - objects from notebook.nbextensions where notebook-4.2-compatible versions
   are available
 - versions from notebook_compat._compat.nbextensions shim scripts otherwise

and similarly for objects from notebook_compat.serverextensions
"""
