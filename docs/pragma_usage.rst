Annotating a TwinCAT3 project 
=============================

Pytmc is capable of generating most of the DB file but some settings require
human direction. Developers set this configuration by adding an attribute
pragma to TwinCAT3 variables when they're declared. These pragmas can be
appended to variables in project files and library files.

Data and Record Types
'''''''''''''''''''''

TwinCAT data types and their corresponding record types are as follows:


+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| Data type |       Lower bound        |       Upper bound       | Memory space |   Record Type   |    Scalar DTYP     |              Waveform DTYP              |
+===========+==========================+=========================+==============+=================+====================+=========================================+
| BOOL      | 0                        | 1                       | 8 bit        | bi, bo          |  asynInt32         | asynInt8ArrayIn, asynInt8ArrayOut       |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| BYTE      | 0                        | 255                     | 8 bit        | longin, longout |  asynInt32         | asynInt8ArrayIn, asynInt8ArrayOut       |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| SINT      | -128                     | 127                     | 8 bit        | longin, longout |  asynInt32         | asynInt8ArrayIn, asynInt8ArrayOut       |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| USINT     | 0                        | 255                     | 8 bit        | longin, longout |  asynInt32         | asynInt8ArrayIn, asynInt8ArrayOut       |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| WORD      | 0                        | 65535                   | 16 bit       | longin, longout |  asynInt32         | asynInt16ArrayIn, asynInt16ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| INT       | -32768                   | 32767                   | 16 bit       | longin, longout |  asynInt32         | asynInt16ArrayIn, asynInt16ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| UINT      | 0                        | 65535                   | 16 bit       | longin, longout |  asynInt32         | asynInt16ArrayIn, asynInt16ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| ENUM      | 0                        | 4294967295              | 32 bit       | longin, longout |  asynInt32         | asynInt16ArrayIn, asynInt16ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| DWORD     | 0                        | 4294967295              | 32 bit       | longin, longout |  asynInt32         | asynInt32ArrayIn, asynInt32ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| DINT      | -2147483648              | 2147483647              | 32 bit       | longin, longout |  asynInt32         | asynInt32ArrayIn, asynInt32ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| UDINT     | 0                        | 4294967295              | 32 bit       | longin, longout |  asynInt32         | asynInt32ArrayIn, asynInt32ArrayOut     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| LWORD     | 0                        | 2**64-1                 | 64 bit       | N/A             |  N/A               | N/A                                     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| LINT      | -2**63                   | 2**63-1                 | 64 bit       | N/A             |  N/A               | N/A                                     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| ULINT     | 0                        | 2**64-1                 | 64 bit       | N/A             |  N/A               | N/A                                     |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| REAL      | -3.4E\+38                | 3.4E\+38                | 32 bit       | ai, ao          |  asynFloat64       | asynFloat32ArrayIn, AsynFloat32ArrayOut |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| LREAL     | -1.797693134862316e\+308 | 1.797693134862358e\+308 | 64 bit       | ai, ao          |  asynFloat64       | asynFloat64ArrayIn, AsynFloat64ArrayOut |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+
| STRING    |                          |                         | Varies       | waveform        |  asynFloat64       | asynInt8ArrayIn, asynInt8ArrayOut       |
+-----------+--------------------------+-------------------------+--------------+-----------------+--------------------+-----------------------------------------+


Lines marked as N/A are not supported by pytmc.


Pragma syntax
'''''''''''''

At a minimum, developers must specify a PV. Specifying an IO direction for each
field is recommended but not required. This would look like the following:

.. code-block:: none 
   
   {attribute 'pytmc' := '
       pv: TEST:MAIN:SCALE
       io: i
   '}
   scale : LREAL := 0.0;

The ``{attribute 'pytmc' := '`` and ``'}`` specify the beginning and end of the
pragma that pytmc will recognize. The middle two lines specify the
configuration for this variable.

Pytmc uses a custom system of configuration where newlines and white space in
a line is important. All lines begin with a title and the title ends before the
colon. All parts thereafter are the 'tag' or the configuration state for this
setting. Some title types such as `field` can have multiple settings for a
single PV.

A pragma with more specification might look like the following:

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


Declaring top level variables
''''''''''''''''''''''''''''''
This is an example of the simplest configuration a developer can provide to
instantiate a variable.

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: TEST:MAIN:SCALE
       io: input
   '}
   scale : LREAL := 0.0;


The developer must specify the PV name (``pv:`` line). All other fields are
optional. We recommend that the user specif the direction of the
data (``io:`` line) however. 

Pytmc needs no additional information but users have the option to override
default settings manually. For example a developer can specify ``scan:`` field
(configures how and when the value is updated) even though this is not
required. For additional information on all the pragma fields, consult the 
`Pragma fields`_ section.


Declaring encapsulated variables
''''''''''''''''''''''''''''''''
Variables declared inside of data structures can be processed by pytmc so long
as each level of encapsulation, all the way down to the first level, is marked
for pytmc. 

The instantiation of encapsulating data types only needs the ``pv:`` line. The
instantiation of a function block could resemble the following:

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: TEST:MAIN:COUNTER_B
   '}
   counter_b : counter;

A variable declared within the ``counter`` function block could resemble the
following:

.. code-block:: none
  
   {attribute 'pytmc' := '
       pv: VALUE
       io: i
   '}  
   value_d : DINT; 


When combined, the PV specified at the instantiation of the user-defined data
type will be appended to the beginning of the PV for all data types defined
within. Each step further into a data structure can add an additional section
to the PV. In the example above the final PV will be
``TEST:MAIN:COUNTER_B:VALUE``. The colons are automatically included. 

This can be recursively applied to data types containing data types.

Information other than the PV name name can be specified at the datatype
instantiation if you wish to make generalizations about the variables
contained inside. These generalizations are overridden if the same field is
specified either on a contained datatype or variable.

For example the following code block will assign a ``field:`` of ``SCAN 1
second`` to all the variables and datatypes that it contains unless they
specify their own version of the  

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: BASE 
       field: SCAN 1 second
   '}
   counter_b : counter;


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


Declaring bidirectional PVs
'''''''''''''''''''''''''''
In instances where a single TwinCAT variable should be able to be both written
and read, multiple PVs can be specified. This allows multiple PVs to be tied to
a single TwinCAT variable.

.. code-block:: none

   {attribute 'pytmc' := '
       pv: TEST:MAIN:ULIMIT_R
       io: io
   '}  
   upper_limit : DINT := 5000;

When specifying multiple PVs, the configuration lines all apply to the nearest,
previous ``pv`` line. For example in the code snippet above, ``type: ai`` will
be applied to the ``TEST:MAIN:ULIMIT_R`` pv and the ``type: ao`` will be
applied to ``TEST:MAIN:ULIMT_W``.


Pragma fields
'''''''''''''
The lines of the pragma tell pytmc how to generate the db and proto. This
section contains more specific descriptions of each of the configuration lines.
Many are automatic with the exception of Pv

pv
..
This constructs the PV name that will represent this variable in EPICS. It is
the only mandatory configuration line. This line can be used on specific
variables as well as the instantiations of data types. When used on variables
declared in the main scope, the PV for the variable will be generated verbatim.
When used on instantiations, this string will be appended to the front of any
PVs that are declared within the data type. 

io
..
This is a guessed field that defaults to 'io'.Specify the whether the IOC is
reading or writing this value. Values being sent from the PLC to the IOC should
be marked as input with 'i' or 'input' and values being sent to the PLC from
the IOC should be marked 'o' or 'output'.  Bidirectional PVs can be specified
with 'io'.

type
....
This is a guessed field and does not need manual specification. This specifies
the EPICS record type. For more information about EPICS records, read this page
from the `EPICS wiki <https://wiki-ext.aps.anl.gov/epics/index.php/RRM_3-14>`_.
Due to the ADS driver records for variables that aren't array-like are
typically of type ai or ao.

fields
......
This is a guessed field and does not need manual specification. This specifies
the lines that will be placed in the epics db as 'fields'.  Multiple field
lines are allowed. These lines determine the PV's behaviors such as alarm
limits and scanning frequency.  Each field specified in the db corresponds to a
field line in the pragma.  Almost all PVs will have multiple fields and hence
multiple field lines in the pragma. The field line has two sections, the field
type and the argument. The field type is the first string of characters up
until the first character of whitespace. It us usually an all-caps abbreviation
like RVAL, DTYP or EGU. This determines the type of field being set. All
characters after the first space are treated as the argument to the field. The
argument can include any characters including spaces and is only broken on a
new line. The INP and OUT fields are generated automatically so there is no
need to manually include them.

SCAN
....
The ``SCAN`` field is special. Pytmc will guess a scan field if not provided
but like ``io`` and ``pv``, the correct setting may be subjective. We would
encourage developers to be aware of this setting. Binary fields default to
``I/O Intr`` for gets. All others default to a polling period of ``.5 second``
for reads and ``Passive`` for gets.

