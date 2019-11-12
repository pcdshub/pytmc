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
setting. Some title types such as ``field`` can have multiple settings for a
single PV.

A pragma could have multiple fields specified. For example, an ``ai`` record 
``TEST:MAIN:SCALE`` would be generated from the following, with a slope of
2.0 and an offset of 1.0, updating only at a rate of once per second:

.. code-block:: none 
   
   {attribute 'pytmc' := '
       pv: TEST:MAIN:SCALE
       io: i
       field: SCAN 1 second
       field: AOFF 1.0
       field: ASLO 2.0
   '}
   scale : LREAL := 0.0;


Reducing update rate
''''''''''''''''''''

By default, all records will have a scan rate of ``I/O Intr``. This means that
even if the value updates on every PLC cycle, EPICS will see (most) of those
events.

In the case of values that update quickly, it may be preferable to reduce
the rate at which EPICS sees updates. This can be done by setting the
`SCAN` field to poll at a fixed rate.

Declaring top level variables
''''''''''''''''''''''''''''''
This is an example of the simplest configuration a developer can provide to
instantiate a variable.

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: TEST:MAIN:SCALE
       io: i
   '}
   scale : LREAL := 0.0;


The developer must specify the PV name (``pv:`` line). All other fields are
optional. We recommend that the user specify the direction of the
data (``io:`` line) however. 

Pytmc needs no additional information but users have the option to override
default settings manually. For example a developer can specify the ``SCAN``
field , which configures how and when the value is updated, even though this is
not required. For additional information on all the pragma fields, consult the 
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
specify their own setting for ``SCAN``.  

.. code-block:: none 

   {attribute 'pytmc' := '
       pv: BASE 
       field: SCAN 1 second
   '}
   counter_b : counter;


.. code-block:: none
  
   {attribute 'pytmc' := '
       pv: VALUE_F_R
       field: SCAN 1 second
       io: i
   '}  
   value_d : DINT; 


Declaring bidirectional PVs
'''''''''''''''''''''''''''
In instances where a single TwinCAT variable should be able to be both written
and read, multiple PVs can be specified. This allows multiple EPICS records to
be tied to a single TwinCAT variable.

.. code-block:: none

   {attribute 'pytmc' := '
       pv: TEST:MAIN:ULIMIT
       io: io
   '}  
   upper_limit : DINT := 5000;


In this case, two records will be generated: ``TEST:MAIN:ULIMIT`` and
``TEST:MAIN:ULIMIT_RBV``.


Pragma fields
'''''''''''''
Each line of the pragma indicates to pytmc how to generate the corresponding records
in the database file output.

pv
..
This constructs the PV name that will represent this variable in EPICS. It is
the only mandatory configuration line. This line can be used on specific
variables as well as the instantiations of data types. 

When used on variables declared in the main scope, the PV for the variable will
be generated verbatim.  When used on instantiations, this string will be
appended to the front of any PVs that are declared within the data type. 

io
..
This is a guessed field that defaults to `'io'`.  Specify the whether the IOC
is reading or writing this value. Values being sent from the PLC to the IOC
should be marked as input with 'i' and values being sent to the PLC from the
IOC should be marked 'o'.  Bidirectional PVs can be specified with 'io'.

fields
......
This specifies additional field(s) to be set on the generated EPICS record(s).
Multiple field lines are allowed. These lines determine the PV's behaviors such
as alarm limits and scanning frequency.  

The format is as follows:

.. code-block:: none

   field: FIELD_NAME field value


This would correspond to a field in the record being generated as follows:

.. code-block:: none

   record(ai, "my_record") {
      ...
      field(FIELD_NAME, "field value")
   }


SCAN
....
The ``SCAN`` field is special. Pytmc will guess a scan field if not provided
but like ``io`` and ``pv``, the correct setting is on a case-by-case basis.
pytmc itself cannot know at what rate a variable will update on the PLC side.

Valid options for this field are:

.. code-block:: none

   "Passive"
   "I/O Intr"
   "10 second"
   "5 second"
   "2 second"
   "1 second"
   ".5 second"
   ".2 second"
   ".1 second"
