Terminal Usage
==============

Using pytmc
-----------
Once pytmc has been installed in a virtual environment the ``makerecord``
command can be called from the command line to generate the .db file. The
command uses two positional arguments. The first is the input specifying the
location of the .tmc file to be processed. In most TwinCAT projects the .tmc
file will be located in  ``[solution folder]/[project folder]/[plc project]
named [plc project].tmc``.

Command line arguments
----------------------

.. code-block:: none
   
   NAME
      pytmc
   DESCRIPTION
      usage: pytmc TMC_FILE [-o DB_FILE] [-h]
   OPTIONS
      positional arguments:
        INPUT       Path to interpreted .tmc file
        OUTPUT      Path to output .db file
      
      optional arguments:
        -h, --help  show this help message and exit
         

