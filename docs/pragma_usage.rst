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
       field: AOFF 1.0
       field: ASLO 2.0
   '}
   scale : LREAL := 0.0;


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
default settings manually. For information on all the pragma fields, consult
the `Pragma fields`_ section.


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

For example the following code block will assign a ``field:`` of ``DESC test``
to all the variables and datatypes that it contains unless they
specify their own setting for ``DESC``.

.. code-block:: none

   {attribute 'pytmc' := '
       pv: BASE
       field: DESC test
   '}
   counter_b : counter;


.. code-block:: none

   {attribute 'pytmc' := '
       pv: VALUE_F_R
       field: DESC test
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


Arrays
''''''

By default, structures with a pragma will generate PVs for each array index,
including all encapsulated sub-elements that also have an associated pragma.

Depending on the number of elements in the array, the PV name will be
zero-padded to aid in future expansion. Reminding ourselves that array bounds
are inclusive in TwinCAT, the following pragma:

.. code-block:: none

    {attribute 'pytmc' := '
        pv: MY:ARRAY
    '}
    myStructure : ARRAY [0..5] of DUT_MyStructure


would generate these prefixes:

.. code-block:: none

    MY:ARRAY:00:
    MY:ARRAY:01:
    MY:ARRAY:02:
    MY:ARRAY:03:
    MY:ARRAY:04:
    MY:ARRAY:05:


The formatting of this may be customized, but it is not recommended to do so
in general. Adding ``expand: :%.3d`` would extend the zero-padding to 3 digits,
regardless of the number of array elements.

It is also possible to select individual elements or a range of elements from
a large array by way of the ``array`` pragma.

To include only the first 2 elements (0 and 1) of this large 101 element array,
the following pragma could be used:

.. code-block:: none

    {attribute 'pytmc' := '
        pv: MY:ARRAY
        array: 0..1
    '}
    myStructure : ARRAY [0..100] of DUT_MyStructure


The array pragma is flexible, allowing for the following:

============ ====================
Array Pragma Elements Selected
============ ====================
0, 1, 2      0, 1, 2
0..2         0, 1, 2
99..         99, 100
..5          0, 1, 2, 3, 4, 5
..5, 99      0, 1, 2, 3, 4, 5, 99
============ ====================


Pragma fields
'''''''''''''

Format: ``{field}: [value]``

A pragma key or field (before the ``:``) and the value after the ``:`` are used
to generate records in EPICS.

pv
..
This constructs the PV name that will represent this variable in EPICS. It is
the only mandatory configuration line. This line can be used on specific
variables as well as the instantiations of data types.

.. note::

   ``$`` may not be used in pragmas due to some TwinCAT limitations as of
   version 4024.  An alternative character ``@`` may be used in its place for
   pv names.  This can also be customized using the ``macro_character`` pragma
   key.

io
..
This is a field that defaults to `'io'`.  Specify the whether the IOC can only
read or also write the value. Values being sent from the PLC to the IOC should
be marked as input with ``input`` (or equivalently ``i``, ``ro``) and values
being sent to the PLC from the IOC should be marked ``output`` (or equivalently
``o``, ``rw``).

.. note::

   The following are valid for input-only (read-only) pragmas: ``input``, ``i``,
   and ``ro``.

   The following are valid for input-output (read-write) pragmas: ``output``, ``io``,
   ``rw``, and ``o``.


Update rate
...........


Format: ``update: {rate}{s|Hz} [{poll|notify}]``

Example: ``1s``, ``1s poll``, ``2Hz notify``

By default, any given PLC variable will be polled at a rate of T=1s (1Hz).
Other poll rates planned to be available by default may be selected on a
per-record (*) basis: T=.5s (2Hz), T=1s (1Hz), T=2s (.5hz), T=10s (.1Hz), and
T=50s (.02Hz), or as configured by the IOC startup script.

By default, any given PLC variable will be bundled together to be polled at a
fixed rate. This is the recommend means of using the ADS IOC.  Using one of the
default polling rates is the only supported method currently, though these
might be configurable in the future in the IOC startup script.  New poll rates
cannot be created in the TwinCAT code.

To customize the polling rate, specify the desired rate in either seconds or
hertz in an ``update`` pragma key. For example:

.. code-block:: none

   update: 1Hz
   update: 1s
   update: 0.5s
   update: 2Hz


The keyword ``poll`` can also be used to explicitly mark it for polling:

.. code-block:: none

   update: 1s poll

For faster rates, an ADS concept of `notifications`, can be used. These are
conceptually similar to callback-on-change in Python or ``camonitor`` in the
context of EPICS.

Use the ``notify`` keyword in the ``update`` setting to enable this:

.. code-block:: none

   update: 10Hz notify
   update: 0.1s notify

.. note::

   Adding too many of these notifications can significantly slow down a PLC,
   even when specified at slow rates. As such, ``notify`` should be used
   sparingly.

(*) This is on the wishlist for ads-ioc. As of December 2019, all polled
records will be processed at a rate of 1 Hz/the IOC-configured poll rate.


Archiver settings
.................

Format: ``archive: {rate}{s|Hz} [{scan|monitor}]``

Example: ``1s``, ``1s scan``, ``2Hz monitor``


Using the database-generating tool ``pytmc db`` along with the pragma key
``archive`` will automatically generate archiver appliance cron-job compatible
``.archive`` files (i.e., those in ``$IOC_DATA/$IOC/archive/*.archive``).
The cron job will read these files and automatically configure the archiver
to archive the listed PVs.

Without an ``archive`` pragma key, the default setting is ``1s scan``. This
means that your PVs will be archived at a rate of once per second, using the
``scan`` method.

For more information on the two methods, see the `EPICS Archiver Appliance
documentation <https://slacmshankar.github.io/epicsarchiver_docs/faq.html>`_.

.. note::

   If the update frequency is slower than the specified archive frequency, the
   archive frequency will be reduced.

.. note::

   Large arrays will not be archived, regardless of pragma settings.


.. note::

   Additional fields can be specified for archiving through the ``archive_fields``
   key, which is a space-delimited list of field names.

   Example: ``archive_fields: DESC PREC``


Record fields
.............
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

While the ``SCAN`` field is special in EPICS to specify the rate at which
records should be updated, pytmc requires that such configuration be done
through the ``update`` pragma key (see `Update rate`_).

Autosave
........

Autosave fields for individual EPICS records are configured by default with
pytmc. It is possible to customize this behavior with additional pragmas,
optionally specifying different fields for input or output records.

Pass 0 indicates restoring information prior to record initialization on IOC
initialization, whereas pass 1 indicates restoring information after record
initialization. Pass 0 is generally safe and does not cause record processing,
whereas pass 1 is just as if one were to ``caput`` to the record after starting
the IOC. When in doubt, use pass 0 and/or ask an EPICS expert.

To apply to either input or output records, pragma keys ``autosave_pass0`` or
``autosave_pass1`` can be used.

To only apply to input records, pragma keys ``autosave_input_pass0``
``autosave_input_pass1`` can be used.

To only apply to output records, pragma keys ``autosave_output_pass0``
``autosave_output_pass1`` can be used.

For example, a pragma like the following:

.. code-block:: none

   autosave_pass0: VAL DESC


Would result in both input and output records having these fields marked for
autosaving:

.. code-block:: none

   record(ai, "my:record_RBV") {
      ...
      info(autosaveFields_pass0, "VAL DESC")
   }

   record(ao, "my:record") {
      ...
      info(autosaveFields_pass0, "VAL DESC")
   }
