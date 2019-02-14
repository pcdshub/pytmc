Terminal Usage
==============

Using pytmc
-----------
Once pytmc has been installed in a virtual environment the ``pytmc``
command can be called from the command line to generate the .db file. The
command uses two positional arguments. The first is the input specifying the
location of the .tmc file to be processed. In most TwinCAT projects the .tmc
file will be located here:

.. code-block:: none

    [TwinCAT solution folder]/[project folder]/[plc project]/[plc project].tmc

Command line arguments
----------------------

.. code-block:: none
   
    usage: pytmc [-h] INPUT OUTPUT
    
        "pytmc" is a command line utility for generating epics records files from
        TwinCAT3 .tmc files. This program is designed to work in conjunction with
        ESSS' m-epics-twincat-ads driver.
    
    positional arguments:
      INPUT       Path to interpreted .tmc file
      OUTPUT      Path to output .db file
    
    optional arguments:
      -h, --help  show this help message and exit

Using xmltranslate
------------------
Pytmc comes packaged with a small script, ``xmltranslate``. Xmltranslate is for
reading in xml and xml-like files and outputting a more human-readable
translation of the xml. It is intended for debugging and development with
python. For normal XML reading, web browsers often offer much more intuitive
interfaces.
