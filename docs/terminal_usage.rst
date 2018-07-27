Terminal Usage
==============

Using pytmc
----------------
The ``pytmc`` script is the primary tool in the pytmc package. It
automates the creation of epics db and proto files for an EPICS IOC. Before
``pytmc`` can be used, the TwinCAT project must be marked appropriately.
This tells ``pytmc`` how to create the appropriate records from the the
TwinCAT variables.  The resulting IOC depends upon EPICS ADS driver. This
driver is provided by the `European Spallation Source
<https://europeanspallationsource.se/>`_ and is hosted on their `bitbucket page
<https://bitbucket.org/europeanspallationsource/m-epics-twincat-ads>`_.

Once pytmc has been installed in a virtual environment the ``pytmc``
command can be called from the command line. The command uses two positional
arguments. The first is the input specifying the location of the .tmc file to
be processed. In most TwinCAT projects the .tmc file will be located in the
[solution folder]/[project folder]/[plc project] named [plc project].tmc The
second argument is the path and base name for the output proto and db files.
Don't add either of these suffixes to the name as they'll be appended
automatically. The ``-h`` argument can be used access to the script's help
pages. 

Marking the TwinCAT project
---------------------------
Marking the TwinCAT project determines how the epics record will be generated.
The marking process uses custom attribute pragmas to designate variables for
pytmc to process. The pragma should be applied just above the declaration of
the variable you wish to mark. You can read more about the TwinCAT pragma
system `here
<https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_plc_intro/9007201784297355.html&id=>`_.
