User Guide
==========

General Usage
+++++++++++++
Pytmc's primary program can be invoked with the command ``pytmc``. This utility
takes the ``*.tmc`` file generated from a TwinCAT3 project and creates an epics
DB file. In order for pytmc to work properly, the TwinCAT project and its
libraries require annotation. The resulting IOC depends upon EPICS ADS driver. This
driver is provided by the `European Spallation Source
<https://europeanspallationsource.se/>`_ and is hosted on their `bitbucket page
<https://bitbucket.org/europeanspallationsource/m-epics-twincat-ads>`_.

Marking the TwinCAT project
---------------------------
Marking the TwinCAT project determines how the epics record will be generated.
The marking process uses custom attribute pragmas to designate variables for
pytmc to process. The pragma should be applied just above the declaration of
the variable you wish to mark. You can read more about the TwinCAT pragma
system `here
<https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_plc_intro/9007201784297355.html&id=>`_.


.. toctree::
   :maxdepth: 1
   :caption: Contents:

   installation.rst
   terminal_usage.rst
   pragma_usage.rst




Python Usage
++++++++++++
Once installed pytmc and its components can be imported into a python program
or shell like any normal python package. Consult the source code documentation
for specifics. 
