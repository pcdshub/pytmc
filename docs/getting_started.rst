Getting Started
===============

General Usage
+++++++++++++
pytmc has various capabilities that can be accessed using the top-level ``pytmc`` program:

   1. Generating EPICS database files (.db) based on a Beckhoff TwinCAT ``.tmc`` file (``pytmc db``)
   2. Introspecting ``.tmc`` files for their symbols and data types ( ``pytmc debug`` and ``pytmc types``)
   3. Generating full EPICS IOCs based on a provided template (``pytmc iocboot`` and ``pytmc stcmd``)
   4. Parsing, introspecting, and summarizing full TwinCAT projects (``pytmc summary``)
   5. Outlining any TwinCAT XML file (``pytmc xmltranslate``)

In order for pytmc to work properly, the TwinCAT project and its
libraries require annotation. The resulting IOC depends upon EPICS ADS driver. This
driver is provided by the `European Spallation Source
<https://europeanspallationsource.se/>`_ and is hosted on their `bitbucket page
<https://bitbucket.org/europeanspallationsource/m-epics-twincat-ads>`_.

Marking the TwinCAT project
+++++++++++++++++++++++++++
Marking the TwinCAT project determines how the EPICS record will be generated.
The marking process uses custom attribute pragmas to designate variables for
pytmc to process. The pragma should be applied just above the declaration of
the variable you wish to mark. You can read more about the TwinCAT pragma
system `here
<https://infosys.beckhoff.com/english.php?content=../content/1033/tc3_plc_intro/9007201784297355.html&id=>`_.

Best practices for SLAC projects are documented in the `PCDS confluence page
<https://confluence.slac.stanford.edu/display/PCDS/TwinCAT+3+Git+Setup+and+Best+Practices>`_.

Having issues with multiline pragmas and related things? See the `PCDS flight
rules
<https://confluence.slac.stanford.edu/display/PCDS/Beckhoff+Flight+Rules>`_.


Python Usage
++++++++++++
Once installed pytmc and its components can be imported into a python program
or shell like any normal python package. Consult the source code documentation
for specifics. 
