User Guide
==========

Installation
++++++++++++

Obtaining the code
------------------
Download the code via the tagged releases posted on the `github releases page
<https://github.com/slaclab/pytmc/releases>`_ or by cloning the source code
with the following:

.. code-block:: sh

   $ git clone https://github.com/slaclab/pytmc.git

Installing in an environment
----------------------------
Create a python virtual environment using conda and install the package.

Begin by creating an environment and replacing [env-name] with the
name of your environment. If you're installing pytmc in a preexisting
environment, you may skip this step.

.. code-block:: sh

   $ conda create --name [env-name]

Activate your environment. 

.. code-block:: sh

   $ source activate [env-name]

After cloning or unzipping the package, navigate to the base directory of
pytmc. There you will find a file titled setup.py. Run the following command
from this directory. Make sure to install pip in this conda environment prior
to running pip. Using pip in an environment lacking a pip installation will
install pytmc in your root environment.

.. code-block:: sh

   $ pip install .

.. note::

   The snippet above has a '.' at the end. It is very difficult to see with
   certain browsers.

Pytmc should be installed now. This can be tested by seeing if the following
bash command can be found.

.. code-block:: sh
   
   $ makerecord

Alternatively, a python shell can be opened and you can attempt to import
pytmc. 

.. code-block:: python

   >>> import pytmc

.. note::  
   While all of these instructions should work with python environments
   managed by virtualenv and pipenv, only conda has been tested. 


General Usage
+++++++++++++
Pytmc comes with two scripts for users. ``makerecord`` is the primary script
for generating epics db (.db) and their proto (.proto) files from TwinCAT
project's .tmc file. The user must mark the TwinCAT project's variables to
indicate which should receive epics records.  

The second tool, ``xmltranslate``, makes xml and tmc
files human readable. It is intended primarily for debugging. 

Using makerecord
----------------
The ``makerecord`` script is the primary tool in the pytmc package. It
automates the creation of epics db and proto files for an EPICS IOC. Before
``makerecord`` can be used, the TwinCAT project must be marked appropriately.
This tells ``makerecord`` how to create the appropriate records from the the
TwinCAT variables.  The resulting IOC depends upon EPICS ADS driver. This
driver is provided by the `European Spallation Source
<https://europeanspallationsource.se/>`_ and is hosted on their `bitbucket page
<https://bitbucket.org/europeanspallationsource/m-epics-twincat-ads>`_.

Once pytmc has been installed in a virtual environment the ``makerecord``
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

Declaring top level variables
''''''''''''''''''''''''''''''
With a pragma, a variable declaration in a main program will appear similar to
the following:

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: TEST:MAIN:SCALE
       type: ai
       field: DTYP stream
       field: SCAN 1 second
       io: input
       str: %f
   '}
   scale : LREAL := 0.0;

Declaring encapsulated variables
''''''''''''''''''''''''''''''''
Variables declared inside of data structures can be processed by makerecord so
long as each level of encapsulation is marked for pytmc. 

The top level instantiation of a function block could resemble the following:

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: TEST:MAIN:COUNTER_B
   '}
   counter_b : counter;

A variable declaration within the ``counter`` function block could resemble the
following:

.. code-block:: none
  
   {attribute 'pytmc' := '
       pv: VALUE_F_R
       type: ai
       field: DTYP stream
       field: SCAN 1 second
       io: input
       str: %d
   '}  
   value_d : DINT; 


When combined, the PV specified at the instantiation of the user-defined data
type will be appended to the beginning of the PV for all data types defined
within. The final PV will be ``TEST:MAIN:COUNTER_B:VALUE_F_R``. The colons are
automatically included. 

Information other than the PV name should be specified at the level of the
specific variable, not where the data type is instantiated.

This can be recursively applied to data types containing data types.

Declaring bidirectional PVs
'''''''''''''''''''''''''''
In instances where a single TwinCAT variable should be able to be both written
and read, multiple PVs can be specified. This allows multiple PVs to be tied to
a single TwinCAT variable.

.. code-block:: none

   {attribute 'pytmc' := '
       pv: TEST:MAIN:ULIMIT_R
       type: ai
       field: DTYP stream
       field: SCAN 1 second
       io: input
       str: %d
       pv: TEST:MAIN:ULIMIT_W
       type: ao
       field: DTYP stream
       io: out
       str: %d
   '}  
   upper_limit : DINT := 5000;

When specifying multiple PVs, the configuration lines all apply to the nearest,
previous ``pv`` line. For example in the code snippet above, ``type: ai`` will
be applied to the ``TEST:MAIN:ULIMIT_R`` pv and the ``type: ao`` will be
applied to ``TEST:MAIN:ULIMT_W``. 

Pragma fields
'''''''''''''
The lines of the pragma tell makerecord how to generate the db and proto. This
section contains more specific descriptions of each of the configuration lines.

pv
..
This specifies the PV name that will represent this variable  in EPICS. This
line can be used on specific variables as well as the instantiations of data
types. When used on variables declared in the main scope, the PV for the
variable will be generated verbatim. When used on instantiations, this string
will be appended to the front of any PVs that are declared within the data
type. 

type
....
This specifies the EPICS record type. For more information about EPICS records,
read this page from the `EPICS wiki
<https://wiki-ext.aps.anl.gov/epics/index.php/RRM_3-14>`_. Due to the ADS
driver records for variables that aren't array-like are typically of type ai or
ao.

field
.....
This specifies the lines that will be placed in the epics db as 'fields'. These
lines determine the PV's behaviors such as alarm limits and scanning frequency.
Each field specified in the db corresponds to a field line in the pragma.
Almost all PVs will have multiple fields and hence multiple field lines in the
pragma. The field line has two sections, the field type and the argument. The
field type is the first string of characters up until the first character of
whitespace. It us usually an all-caps abbreviation like RVAL, DTYP or EGU. This
determines the type of field being set. All characters after the first space
are treated as the argument to the field. The argument can include any
characters including spaces and is only broken on a new line. The INP and OUT
fields are generated automatically so there is no need to manually include
them.

io
..
Specify the whether the IOC is reading or writing this value. Values being sent
from the PLC to the IOC should be marked as input with 'i' or 'input' and
values being sent to the PLC from the IOC should be marked 'o' or 'output'.

str
...
Specify how to format the data for the ADS interface. E.g. use ``%s``, ``%d``,
and ``%f`` as if this were a C/C++ program.

init
....
Variables with both read and write variables can use ``init: true`` to indicate
that the initial value of the writable value should be initialized as the
current value read from this PV. The init line should be attached to the output
PV. Given that the ADS driver is moving away from using the proto file, this
field may be deprecated soon. 

Automatic lines
'''''''''''''''
The goal of pytmc is to make IOC creation much faster and less error prone.
Makerecord's goal is to guess as many of the configuration lines as possible.
To allow pytmc to guess the lines, do not include them in the pragma. If you
wish to override a value that is normally guessed, write the line into the
pragma. Pytmc is still in development and this list will grow with time. The
latest version of pytmc can guess the following lines:

 - INP and OUT fields 

Python Usage
++++++++++++
Once installed pytmc and its components can be imported into a python program
or shell like any normal python package. Consult the source code documentation
for specifics. 
