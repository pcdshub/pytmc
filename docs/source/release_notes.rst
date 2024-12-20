=================
 Release History
=================

v2.17.0 (2024-12-19)
====================

Changes
-------
- Adds support for arrays of strings

Maintenance
-----------
- Add `setuptools_scm` to conda recipe build section


v2.17.0 (2024-09-16)
====================

This version fixes an issue where there was no way for `ads-ioc` to enforce
read-only behavior on the `_RBV` variants. This led to confusing behavior
because the IOC will accept these writes and not respond to them in an
intuitive way.

`pytmc` will now generate input/rbv records as having the `NO_WRITE` ASG.
This will affect all PVs that represent data read from the PLC code. It will not affect the setpoints.

`ads-ioc` can now implement a `NO_WRITE` ASG and it will be applied to all of these PVs.
This is expected in `ads-ioc` at `R0.7.0`.


v2.16.0 (2023-07-31)
====================

Changes
-------

* ``pytmc template``, which takes a TwinCAT project and jinja template source
  code to generate project-specific output, now expects all platforms to use
  the same delimiter (``":"``) for template filename patterns. Examples include:

  * Read template from ``a.template`` and write expanded version to ``a.txt``:
    ``pytmc template my.tsproj --template a.template:a.txt``
  * Read template from ``a.template`` and write results to standard output:
    ``pytmc template my.tsproj --template a.template``
  * Read template from standard input and write results to standard output:
    ``pytmc template my.tsproj --template -``
  * Read template from standard input and write results to ``/path/to/a.txt``:
    ``pytmc template my.tsproj --template -:/path/to/a.txt``

* Extended support for projects not correctly configured in TwinCAT with
  "Independent Files" for all supported options.  Generating EPICS IOCs
  from such projects that also include NC axes should succeed with
  a number of loud warnings to the user.

Maintenance
-----------

* Fixed old release note syntax.


v2.15.1 (2023-06-30)
====================

Bugfixes
--------
- Type aliases will now find pytmc pragmas defined on their base types.
  Previously these were ignored.
- ST_MotionStage is now the canonical name for the motor struct,
  matching our twincat style guide. Backwards compatibility is retained
  for projects using DUT_MotionStage.
- Fix an issue where macro substitution did not load properly for
  motor base PVs in the st.cmd file generation.
- Fix an issue where the version could fail to load in an edge case
  where a git clone was included via symbolic link.

Maintenance
-----------
- Ensure workflow secrets are used properly.
- Fix issues related to documention building on the Github actions CI.


v2.15.0 (2023-04-04)
====================

Python 3.9 is now the minimum supported version for pytmc.

Maintenance
-----------
* Fixes pre-commit repository settings for flake8.
* Migrates from Travis CI to GitHub Actions for continuous integration testing, and documentation deployment.
* Updates pytmc to use setuptools-scm, replacing versioneer, as its version-string management tool of choice.
* Syntax has been updated to Python 3.9+ via ``pyupgrade``.
* pytmc has migrated to modern ``pyproject.toml``, replacing ``setup.py``.
* Sphinx 6.0 now supported for documentation building.
* ``docs-versions-menu`` is now used for documentation deployment on GitHub Actions.


v2.14.1 (2022-09-28)
====================

This release doesn't change any behavior of the library, but it does fix an error in the test suite that causes false failures.

Maintenance
-----------

* TST: test suite was using old kwarg, swap to new by @ZLLentz in #296


v2.14.0 (2022-08-29)
====================

Fixes
-----
* Safety PLC files loaded from `_Config/SPLC` by @klauer in https://github.com/pcdshub/pytmc/pull/289

Enhancements
------------

* Sort generated records by TwinCAT symbol name (tcname) by @klauer in https://github.com/pcdshub/pytmc/pull/293
* The order of records in EPICS process database (`.db`) files will change for most users after this release. After the initial rebuild, users should expect to see smaller diffs on subsequent PLC project rebuilds.
* Add all hooks required to allow transition of pytmc stcmd -> template by @klauer in https://github.com/pcdshub/pytmc/pull/290

  * Adds helper commands to `pytmc template`, which can be used in Jinja templates:

    * `generate_records` (create .db and .archive files)
    * `get_plc_by_name`
    * `get_symbols_by_type`

  * Adds variables to `pytmc template` environment, which can be used in Jinja templates: `pytmc_version`

  * Adds `--macro` option to `pytmc template`
  * Fixes some annotations + uncovered/untested functionality
  * Allows `pytmc template` to read/write multiple templates with parsing a project only once


v2.13.0 (2022-06-30)
====================

Enhancements
------------
* ENH: autosave field additions by @klauer in https://github.com/pcdshub/pytmc/pull/287
    * Adds description field to autosave for all records, input and output
    * Adds alarm severity and limit fields to autosave for all relevant input and output records
    * Adds control limit (drive low/high) fields to autosave for relevant output records

v2.12.0 (2022-05-27)
====================

Fixes
-----
* CP link instead of CPP link by @klauer in https://github.com/pcdshub/pytmc/pull/283

Maintenance
-----------
* Address CI-related failures and update pre-commit settings by @klauer in https://github.com/pcdshub/pytmc/pull/285


v2.11.1 (2022-03-24)
====================

Maintenance
-----------

* CLN: remove evalcontextfilter usage by @klauer in #280
   * Jinja2 3.1 compatibility fix
* TST: does linking work as expected? by @klauer in #279
   * Additional tests

v2.11.0 (2021-11-15)
====================

Enhancements
------------
* Add ``EnumerationTextList`` with ``get_source_code`` support.
  Previously, these translatable types were missing.
* Add actions, methods, and properties to the ``pytmc code`` output.
* Allow for ``pytmc code`` to work with just a single code object,
  rather than requiring the whole project.
* Add ``pytmc.__main__`` such that
  ``python -m pytmc {code,summary} ...`` works.

Fixes
-----
* Fix rare bug in `lines_between` function, probably never hit.

Maintenance
-----------
* Type annotation cleanups and fixes
* Reduce memory consumption slightly by not caching the xml element
  on every `TwincatItem`


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
