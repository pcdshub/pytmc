User Guide
==========

Installation
++++++++++++

Obtaining the program
---------------------

Download the code via the tagged releases posted on `github releases
<https://github.com/slaclab/pytmc/releases>`_ or by cloning the source code
with the following:

.. code-block:: sh

   $ git clone https://github.com/slaclab/pytmc.git



Installing in an environment
----------------------------

Create a python virtual environment with conda and install the package.

Begin by creating an environment if necessary and replacing [env-name] with the
name of your environment.

.. code-block:: sh

   $ conda create --name [env-name]

Enter your environment

.. code-block:: sh

   $ source activate [env-name]

Navigate to the base directory of pytmc. There you will find a file titled
setup.py. Run the following command from this directory. Make sure to install
pip in this conda environment prior to running pip. Using pip in an environment
lacking a pip installation will install pytmc in your root environment. 

.. code-block:: sh

   $ pip install .

Pytmc should be installed now. This can be tested by seeing if the following
bash command can be found.

.. code-block:: sh
   
   $ makerecord

Alternatively, a python shell can be opened and you can attempt to import
pytmc. 

.. code-block:: python

   import pytmc

While all of these instructions should work with python environments managed by
virtualenv and pipenv, this has not been tested.  



General Usage
+++++++++++++

Using makerecord


Python Usage
++++++++++++

Instructions for using python methods
