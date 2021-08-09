=================
 Release History
=================

v2.10.0 (2021-08-09)
====================

Enhancements
------------
* Allow strings to be linked using the ``link:`` pragma key. Previously,
  this was only implemented for numeric scalar values.


v2.9.1 (2021-04-27)
===================

Enhancements
------------
* Added ``scale`` and ``offset`` pragma keys for integer and floating point
  symbols.

Maintenance
-----------
* Fixed remaining ``slaclab`` references, after the repository was moved to
  ``pcdshub``.


v2.9.0 (2021-04-02)
===================

Enhancements
------------
* Add git information to the template tool if available.


v2.8.1 (2021-02-10)
===================

Fixes
-----
* Fix issues related to insufficient library dependency checking. Now,
  all possible places where library version information is stored will
  be checked.

Maintenance
-----------
* Refactor the dependency-related twincat items and templating tools
  to accomplish the above.
* Move the repository landing zone from slaclab to pcdshub to take
  advantage of our travis credits.
* Redeploy doctr for pcdshub.


v2.8.0 (2020-12-22)
===================

Enhancements
------------

* Add support for externally adding pragmas to members of structures and
  function blocks.
* Add support for partial pragmas of array elements.
* Added text filter in ``pytmc debug`` dialog.
* Check maximum record length when generating the database file.  This is a
  constant defined at epics-base compile time, defaulting to 60.

Fixes
-----

* Record names now displaying correctly in ``pytmc debug`` dialog.
* ``pytmc debug`` no longer fails when it encounters types that extend
  built-in data types by way of ``ExtendsType``.


v2.7.7 (2020-11-17)
===================

Fixes
-----
* Fix issue with pass1 autosave not appropriately writing values to the PLC
  on IOC startup.

Maintenance
-----------
* Regenerate doctr deploy key.


v2.7.6 (2020-10-23)
===================

Fixes
-----
* Added handling for case where pragma is None
* Lower array archive threshold to arrays with fewer than 1000 elements
  to prevent our high-rate encoder and power meter readbacks. This is a good
  threshold because it represents 1000Hz data with a 1Hz polling rate, a
  very typical parameter.
* Default APST and MPST fields to "On Change" for waveform PVs. These are
  special waveform fields that tell monitors and the archiver when to take an
  update, and previously they were set to "Always", causing influxes of data
  from static char waveform strings.

Maintenance
-----------
* Split dev/docs requirements
* Fix jinja naming


v2.7.5 (2020-08-31)
===================

Fixes
-----

* Relaxed end-of-pragma-line handling (any combination of ``;`` and newline are
  all accepted).
* Reworked XTI file loading for "devices" and "boxes".  This aims to be more
  compatible with TwinCAT, which does not always relocate XTI files to be in
  the correct hierarchical directory location.  It pre-loads all XTI files, and
  when the project is fully loaded, it dereferences XTI files based on a key
  including ``class``, ``filename``, and a small PLC-unique ``identifier``.
* Better handling of data types in the project parser. Now supports data type
  GUIDs, when available, for data type disambiguation.  Note that these are not
  always present.
* Better handling of references, pointers, and pointer depth.

Development
-----------

* ``pytmc db --debug`` allows developers to more easily target exceptions
  raised when generating database files.
* Added more memory layout information for the benefit of other utilities such
  as ``ads-async``. Its ADS server implementation in conjunction with pytmc may
  be a good source of information regarding PLC memory layout in the future.
* Started adding some annotations for clarity.  May retroactively add more as
  time permits.


v2.7.1 (2020-08-18)
===================

Fixes
-----

* Working fix for macro expansion character replacement for linked PVs
  (``DOL`` field).  This means ``link: @(MACRO)PV`` now works.
* Tests will no longer be installed erroneously as a package on the system.

Development
-----------

* Tests have been moved into the pytmc package, and with it flake8 compliance.


v2.7.0 (2020-07-16)
===================

* Included an incomplete fix for macro expansion character replacement for
  linked PVs (``DOL`` field)


v2.6.9 (2020-07-06)
===================

*  Fixes pragmalint bug that fails on an empty declaration section


v2.6.8 (2020-07-06)
===================

*  Fixes issue where qtpy/pyqt not being installed may cause ``pytmc``
   command-line tools to fail


v2.6.7 (2020-07-02)
===================

*  Project-level data type summary
*  Create DataArea for data type summary if unavailable in .tmc


v2.6.6 (2020-06-24)
===================

*  Add –types (–filter-types) to ``pytmc summary``
   (`#213 <https://github.com/pcdshub/pytmc/issues/213>`__)
*  Fix internal usage of deprecated API
   (`#212 <https://github.com/pcdshub/pytmc/issues/212>`__)


v2.6.5 (2020-06-09)
===================

*  Add ``info(archive)`` nodes for ads-ioc
   (`#188 <https://github.com/pcdshub/pytmc/issues/188>`__)
*  Adjust defaults for binary record enum strings
   (`#191 <https://github.com/pcdshub/pytmc/issues/191>`__)
*  Better messages on pragma parsing failures
   (`#200 <https://github.com/pcdshub/pytmc/issues/200>`__)
*  Do not include fields only intended for input/output records in the
   other (`#205 <https://github.com/pcdshub/pytmc/issues/205>`__)
*  (Development) Fix package manifest and continuous integration


v2.6.0 (2020-02-26)
===================

*  Fix FB_MotionStage pointer-handling in st.cmd generation
*  Fix off-by-one array bounds error
*  Expose actions in summary + generate more readable code block output
*  Fix autosave info node names
*  Ensure ``--allow-errors`` is passed along to the database generation
   step when using ``pytmc stcmd``
*  Allow ``pytmc db`` to work with the ``.tsproj`` file along with
   ``.tmc`` file
*  Add initial “PV linking” functionality (to be completed + documented;
   paired with lcls-twincat-general)
*  Fix bug where Enum info may be missing from the .tmc file
*  Show the chain name of a failed record generation attempt
*  Fix loading of ``_Config/IO`` files in certain cases, though there is
   still work to be done here
   (`#187 <https://github.com/pcdshub/pytmc/issues/187>`__


v2.5.0 (2019-12-20)
===================

Features
--------

* Debug tool option for showing variables which do not generate records (`#159 <https://github.com/pcdshub/pytmc/issues/159>`__) “incomplete pragmas/chains”
* Automatic generation of archive support files (`#162 <https://github.com/pcdshub/pytmc/issues/162>`__)
* Support customization of update rates via poll/notify (`#151 <https://github.com/pcdshub/pytmc/issues/151>`__), looking forward to new m-epics-twincat-ads releases
* Support record aliases (`#150 <https://github.com/pcdshub/pytmc/issues/150>`__)
* Description defaults to PLC variable path if unspecified (`#152 <https://github.com/pcdshub/pytmc/issues/152>`__)

Fixes
-----
* Ordering of autosave fields (`#154 <https://github.com/pcdshub/pytmc/issues/154>`__)
* Box summary ordering (`#164 <https://github.com/pcdshub/pytmc/issues/164>`__)
* Allow alternative character for EPICS macros (default ``@``)
* Documentation updates + pragma key clarification


v2.4.0 (2019-12-06)
===================

Features
--------

* Pinned global variables are supported
* Autosave support
* Pypi integration

Enhancements
------------

* Linter/Debugger improvements
* Debug shows relative paths

Fixes
-----

* Record sorting is now deterministic

Pull requests incorporated
--------------------------

* `#130 <https://github.com/pcdshub/pytmc/issues/130>`__
* `#135 <https://github.com/pcdshub/pytmc/issues/135>`__
* `#137 <https://github.com/pcdshub/pytmc/issues/137>`__
* `#138 <https://github.com/pcdshub/pytmc/issues/138>`__
* `#141 <https://github.com/pcdshub/pytmc/issues/141>`__
* `#142 <https://github.com/pcdshub/pytmc/issues/142>`__
* `#143 <https://github.com/pcdshub/pytmc/issues/143>`__
* `#144 <https://github.com/pcdshub/pytmc/issues/144>`__


v2.3.1 (2019-11-08)
===================

Fixes
-----

* Fixed an issue where Enums weren’t being handled correctly
* pytmc now allows the declaration/implementation to be ``None`` allowing these
  sections to be empty without breaking
* Some windows file reading issues have been resolved

Refactors
---------
* Move pragma checking code to from ``Datatype.walk`` to ``SubItem.walk`` for
  an implementation more consistent with ``Symbol.walk``


v2.3.0 (2019-10-28)
===================

PRs
---
* `#123 <https://github.com/pcdshub/pytmc/issues/123>`__,
* `#124 <https://github.com/pcdshub/pytmc/issues/124>`__, and
* `#125 <https://github.com/pcdshub/pytmc/issues/125>`__ to an official release.

Features
--------
* Add Support For NC axis parameters
* ``.sln`` files may now be passed to ``pytmc summary``

Fixes
-----
* ``pytmc`` now identifies and handles T_MaxString


v2.2.0 (2019-09-20)
===================

Enhancements
------------

* Adds support for arrays of complex datatypes.
* Replaces FB_MotionStage support with DUT_MotionStage.
* Converts ’_’ in project name in TC3 to ‘-’ in ioc name following convention.

Fixes
-----

* ``stcmd`` generation updated to match changes to ``pragmas`` functionality solving some incompatibilites
* Switch to DUT_MotionStage namespace allows motors above 0-9 range.


v2.1.0 (2019-09-05)
===================

This tag includes the new pragma linting features for assessing whether
TwinCAT3 projects are PyTMC compatible.

This feature can be accessed using this command:
``pytmc pragmalint [-h] [--markdown] [--verbose] filename``


v1.1.2 (2019-03-15)
===================

Features
--------

*  Pragmas can now be delimited with semicolons # Bugfixes
*  Spaces after the first semicolon in a pragma no longer break pragmas
*  Blank PV strings no longer lead to the creation of multiple colons in
   a PV name
*  Single line pragmas are properly recognized now


v1.1.1 (2019-02-14)
===================

This release rectifies several issues with the command line interface.
The primary command is now ``pytmc`` replacing the old ``makerecord``.

Tests for python 3.7 have been implemented.


v1.1.0 (2018-10-16)
===================

Incorporate support for a greater set of TwinCAT Datatypes.


v1.0.0 (2018-09-24)
===================

First major release.


v0.1 (2018-03-02)
=================

Primary features of .db and .proto file creation have been implemented.
Compatibility with enums, aliases, waveforms/arrays, field guessing
tools, and a user guide have not been implemented.
