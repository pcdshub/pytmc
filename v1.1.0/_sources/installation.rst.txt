Installation
============

Obtaining the code
++++++++++++++++++
Download the code via the tagged releases posted on the `github releases page
<https://github.com/slaclab/pytmc/releases>`_ or by cloning the source code
with the following:

.. code-block:: sh

   $ git clone https://github.com/slaclab/pytmc.git

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

After cloning or unzipping the package, navigate to the base directory of
pytmc. There you will find a file titled ``setup.py`` and another titles
``requirements.txt``. Run the following commands from this directory. Make sure
to install pip in this conda environment prior to installing tools with pip.
Using pip in an environment lacking a pip installation will install pytmc in
your root environment.

.. code-block:: sh

   $ conda install pip
   $ pip install -r requirements.txt
   $ pip install .

.. note::

   The last line in the code snippet above has a '.' at the end. It is very
   difficult to see with certain browsers.


Testing the installation
++++++++++++++++++++++++
Pytmc should be installed now. This can be tested by seeing if the following
bash commands can be found.

.. code-block:: sh
   
   $ pytmc --help

Alternatively, a python shell can be opened and you can attempt to import
pytmc. 

.. code-block:: python

   >>> import pytmc

.. note::  
   While all of these instructions should work with python environments
   managed by virtualenv and pipenv, only conda has been tested. 
