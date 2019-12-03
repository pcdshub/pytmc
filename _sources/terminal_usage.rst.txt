Command-line Usage
==================

Using pytmc
-----------
Once pytmc has been installed in a virtual environment the ``pytmc`` command
can be called from the command line to generate .db files and more.


pytmc db
--------

.. argparse::
   :module: pytmc.bin.db
   :func: build_arg_parser
   :prog: pytmc db


pytmc stcmd
-----------

.. argparse::
   :module: pytmc.bin.stcmd
   :func: build_arg_parser
   :prog: pytmc stcmd


pytmc xmltranslate
------------------

.. argparse::
   :module: pytmc.bin.xmltranslate
   :func: build_arg_parser
   :prog: pytmc xmltranslate


pytmc debug
-----------

.. argparse::
   :module: pytmc.bin.debug
   :func: build_arg_parser
   :prog: pytmc debug


pytmc pragmalint
----------------

.. argparse::
   :module: pytmc.bin.pragmalint
   :func: build_arg_parser
   :prog: pytmc pragmalint


pytmc stcmd
-----------

.. argparse::
   :module: pytmc.bin.stcmd
   :func: build_arg_parser
   :prog: pytmc stcmd


pytmc summary
-------------

.. argparse::
   :module: pytmc.bin.summary
   :func: build_arg_parser
   :prog: pytmc summary


pytmc types
-----------

.. argparse::
   :module: pytmc.bin.types
   :func: build_arg_parser
   :prog: pytmc types


Templates
=========

stcmd_default.cmd
-----------------

.. include:: ../pytmc/templates/stcmd_default.cmd
   :literal:

asyn_standard_file.jinja2
-------------------------

.. include:: ../pytmc/templates/asyn_standard_file.jinja2
   :literal:


asyn_standard_record.jinja2
---------------------------

.. include:: ../pytmc/templates/asyn_standard_record.jinja2
   :literal:
