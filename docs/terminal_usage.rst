Terminal Usage
==============

Using pytmc
-----------
Once pytmc has been installed in a virtual environment the ``pytmc``
command can be called from the command line. The command uses two positional
arguments. The first is the input specifying the location of the .tmc file to
be processed. In most TwinCAT projects the .tmc file will be located in  
``[solution folder]/[project folder]/[plc project] named [plc project].tmc``.

Command line arguments
----------------------

.. code-block:: none
   
   NAME
      pytmc
   DESCRIPTION
      usage: pytmc TMC_FILE [-o DB_FILE] [-h]
   OPTIONS
      positional arguments:
         TMC_FILE
            The path to the input TMC file
      optional arguments:
         -o DB_FILE
            Specify the output file name if you do not wish to use the
            automatically generated name
         -h, --help
            Display the help text
         

