Installation
============

Obtaining the code
++++++++++++++++++
Download the code via the tagged releases posted on the `github releases page
<https://github.com/pcdshub/pytmc/releases>`_ or by cloning the source code
with the following:

.. code-block:: sh

   $ git clone https://github.com/pcdshub/pytmc.git

Installing in an environment
++++++++++++++++++++++++++++
Create a python virtual environment using conda and install the pytmc in that
environment.

Begin by creating an environment and replacing [env-name] with the
name of your environment. If you're installing pytmc in a preexisting
environment, you may skip this step.

.. code-block:: sh

   $ conda create --name [env-name]

Activate your environment.

.. code-block:: sh

   $ source activate [env-name]

Install pip in the current environment if it is not already. If pip is not
installed in your environment, the system will default to using pip in the root
environment. When the root environment's version of pip is used. Pip will
attempt to install the package in the root envirnoment as well.

.. code-block:: sh

   $ conda install pip

After cloning or unzipping the package, navigate to the base directory of
pytmc. There you will find a file titled ``setup.py`` and another titles
``requirements.txt``. Run the following commands from this directory. Make sure
to install pip in this conda environment prior to installing tools with pip.
Using pip in an environment lacking a pip installation will install pytmc in
your root environment.

.. code-block:: sh

   $ # Install pytmc's dependencies
   $ pip install -r requirements.txt
   $ # Install pytmc to your environment
   $ pip install .

.. note::

   The last line in the code snippet above has a '.' at the end. It is very
   difficult to see with certain browsers.


Testing the installation
++++++++++++++++++++++++
If you've followed the previous steps correctly, pytmc should be installed now.
This can be tested by seeing if the following bash commands can be found.

.. code-block:: sh

   $ pytmc --help

Alternatively, a python shell can be opened and you can attempt to import
pytmc.

.. code-block:: python

   >>> import pytmc

.. note::
   While all of these instructions should work with python environments
   managed by virtualenv and pipenv, only conda has been tested.


Installing for development
++++++++++++++++++++++++++
To develop pytmc it is best to use a development install. This allows changes
to the code to be immediately reflected in the program's functionality without
needing to reinstall the code.This can be done by following the `Installing in
an environment`_ section but with one change. The following code snippet should
be removed:

.. code-block:: sh

   $ # Don't use this step for a development install
   $ pip install .

In place of the removed command, use the following to do a development install.

.. code-block:: sh

   $ # Use this command instead
   $ pip install -e .
