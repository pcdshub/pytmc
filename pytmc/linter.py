import os

import pyPDB.dbd.yacc as _yacc
import pyPDB.dbdlint as _dbdlint
from pyPDB.dbdlint import DBSyntaxError

MAX_RECORD_LENGTH = int(os.environ.get("EPICS_MAX_RECORD_LENGTH", "60"))


class LinterResults(_dbdlint.Results):
    """
    Container for dbdlint results, with easier-to-access attributes

    Extends pyPDB.dbdlint.Results

    Each error or warning has dictionary keys::

        {name, message, file, line, raw_message, format_args}

    Attributes
    ----------
    errors : list
        List of errors found
    warnings : list
        List of warnings found
    """

    def __init__(self, args):
        super().__init__(args)
        self.errors = []
        self.warnings = []

    def _record_warning_or_error(self, result_list, name, msg, args):
        result_list.append(
            {
                "name": name,
                "message": msg % args,
                "file": self.node.fname,
                "line": self.node.lineno,
                "raw_message": msg,
                "format_args": args,
            }
        )

    def err(self, name, msg, *args):
        super().err(name, msg, *args)
        self._record_warning_or_error(self.errors, name, msg, args)

    def warn(self, name, msg, *args):
        super().warn(name, msg, *args)
        if name in self._warns:
            self._record_warning_or_error(self.warnings, name, msg, args)

    @property
    def success(self):
        """
        Returns
        -------
        success : bool
            True if the linting process succeeded without errors
        """
        return not len(self.errors)


class DbdFile:
    """
    An expanded EPICS dbd file

    Parameters
    ----------
    fn : str or file
        dbd filename

    Attributes
    ----------
    filename : str
        The dbd filename
    parsed : list
        pyPDB parsed dbd nodes
    """

    def __init__(self, fn):
        if hasattr(fn, "read"):
            self.filename = getattr(fn, "name", None)
            contents = fn.read()
        else:
            self.filename = str(fn)
            with open(fn) as f:
                contents = f.read()

        self.parsed = _yacc.parse(contents)


def lint_db(
    dbd,
    db,
    *,
    full=True,
    warn_ext_links=False,
    warn_bad_fields=True,
    warn_rec_append=False,
    warn_quoted=False,
    warn_varint=True,
    warn_spec_comm=True,
):
    """
    Lint a db (database) file using its database definition file (dbd) using
    pyPDB.

    Parameters
    ----------
    dbd : DbdFile or str
        The database definition file; filename or pre-loaded DbdFile
    db : str
        The database filename or text
    full : bool, optional
        Validate as a complete database
    warn_quoted : bool, optional
        A node argument isn't quoted
    warn_varint : bool, optional
        A variable(varname) node which doesn't specify a type, which defaults
        to 'int'
    warn_spec_comm : bool, optional
        Syntax error in special #: comment line
    warn_ext_link : bool, optional
        A DB/CA link to a PV which is not defined.  Add '#: external("pv.FLD")
    warn_bad_field : bool, optional
        Unable to validate record instance field due to a previous error
        (missing recordtype).
    warn_rec_append : bool, optional
        Not using Base >=3.15 style recordtype "*" when appending/overwriting
        record instances

    Raises
    ------
    DBSyntaxError
        When a syntax issue is discovered. Note that this exception contains
        file and line number information (attributes: fname, lineno, results)

    Returns
    -------
    results : LinterResults
    """
    args = []
    if warn_ext_links:
        args.append("-Wext-link")
    if warn_bad_fields:
        args.append("-Wbad-field")
    if warn_rec_append:
        args.append("-Wrec-append")

    if not warn_quoted:
        args.append("-Wno-quoted")
    if not warn_varint:
        args.append("-Wno-varint")
    if not warn_spec_comm:
        args.append("-Wno-spec-comm")

    if full:
        args.append("-F")
    else:
        args.append("-P")

    dbd_file = dbd if isinstance(dbd, DbdFile) else DbdFile(dbd)

    args = _dbdlint.getargs([dbd_file.filename, db, *args])

    results = LinterResults(args)

    if os.path.exists(db):
        with open(db) as f:
            db_content = f.read()
    else:
        db_content = db
        db = "<string>"

    try:
        _dbdlint.walk(dbd_file.parsed, _dbdlint.dbdtree, results)
        parsed_db = _yacc.parse(db_content, file=db)
        _dbdlint.walk(parsed_db, _dbdlint.dbdtree, results)
    except DBSyntaxError as ex:
        ex.errors = results.errors
        ex.warnings = results.warnings
        raise

    return results
