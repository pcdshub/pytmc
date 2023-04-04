"""
Code parsing-related utilities
"""
import collections
import logging
import re

logger = logging.getLogger(__name__)


RE_FUNCTION_BLOCK = re.compile(r"^FUNCTION_BLOCK\s", re.MULTILINE)
RE_PROGRAM = re.compile(r"^PROGRAM\s", re.MULTILINE)
RE_FUNCTION = re.compile(r"^FUNCTION\s", re.MULTILINE)
RE_ACTION = re.compile(r"^ACTION\s", re.MULTILINE)


def program_name_from_declaration(declaration):
    """
    Determine a program name from a given declaration

    Looks for::

        PROGRAM <program_name>
    """
    for line in declaration.splitlines():
        line = line.strip()
        if line.lower().startswith("program "):
            return line.split(" ")[1]


def determine_block_type(code):
    """
    Determine the code block type, looking for e.g., PROGRAM or FUNCTION_BLOCk

    Returns
    -------
    {'function_block', 'program', 'function', 'action'} or None
    """
    checks = [
        (RE_FUNCTION_BLOCK, "function_block"),
        (RE_FUNCTION, "function"),
        (RE_PROGRAM, "program"),
        (RE_ACTION, "action"),
        # TODO: others?
    ]
    for regex, block_type in checks:
        if regex.search(code):
            return block_type


def lines_between(text, start_marker, end_marker, *, include_blank=False):
    """
    From a block of text, yield all lines between `start_marker` and
    `end_marker`

    Parameters
    ----------
    text : str
        The block of text
    start_marker : str
        The block-starting marker to match
    end_marker : str
        The block-ending marker to match
    include_blank : bool, optional
        Skip yielding blank lines
    """
    found_start = False
    start_marker = start_marker.lower()
    end_marker = end_marker.lower()
    for line in text.splitlines():
        if line.strip().lower() == start_marker:
            found_start = True
        elif found_start:
            if line.strip().lower() == end_marker:
                break
            elif line.strip() or include_blank:
                yield line


def variables_from_declaration(declaration, *, start_marker="var"):
    """
    Find all variable declarations given a declaration text block

    Parameters
    ----------
    declaration : str
        The declaration code
    start_marker : str, optional
        The default works with POUs, which have a variable block in
        VAR/END_VAR.  Can be adjusted for GVL 'var_global' as well.

    Returns
    -------
    variables : dict
        {'var': {'type': 'TYPE', 'spec': '%I'}, ...}
    """
    variables = {}
    in_type = False
    for line in lines_between(declaration, start_marker, "end_var"):
        line = line.strip()
        if in_type:
            if line.lower().startswith("end_type"):
                in_type = False
            continue

        words = line.split(" ")
        if words[0].lower() == "type":
            # type <type_name> :
            # struct
            # ...
            # end_struct
            # end_type
            in_type = True
            continue

        # <names> : <dtype>
        try:
            names, dtype = line.split(":", 1)
        except ValueError:
            logger.debug("Parsing failed for line: %r", line)
            continue

        if ":=" in dtype:
            # <names> : <dtype> := <value>
            dtype, value = dtype.split(":=", 1)
        else:
            value = None

        try:
            at_idx = names.lower().split(" ").index("at")
        except ValueError:
            specifiers = []
        else:
            # <names> AT <specifiers> : <dtype> := <value>
            words = names.split(" ")
            specifiers = words[at_idx + 1 :]
            names = " ".join(words[:at_idx])

        var_metadata = {
            "type": dtype.strip("; "),
            "spec": " ".join(specifiers),
        }
        if value is not None:
            var_metadata["value"] = value.strip("; ")

        for name in names.split(","):
            variables[name.strip()] = var_metadata

    return variables


def get_pou_call_blocks(declaration: str, implementation: str):
    """
    Find all call blocks given a specific POU declaration and implementation.
    Note that this function is not "smart". Further calls will be squashed into
    one.  Control flow is not respected.

    Given the following declaration::

        PROGRAM Main
        VAR
                M1: FB_DriveVirtual;
                M1Link: FB_NcAxis;
                bLimitFwdM1 AT %I*: BOOL;
                bLimitBwdM1 AT %I*: BOOL;

        END_VAR

    and implementation::

        M1Link(En := TRUE);
        M1(En := TRUE,
           bEnable := TRUE,
           bLimitFwd := bLimitFwdM1,
           bLimitBwd := bLimitBwdM1,
           Axis := M1Link.axis);

        M1(En := FALSE);

    This function would return the following dictionary::

        {'M1': {'En': 'FALSE',
          'bEnable': 'TRUE',
          'bLimitFwd': 'bLimitFwdM1',
          'bLimitBwd': 'bLimitBwdM1',
          'Axis': 'M1Link.axis'},
         'M1Link': {'En': 'TRUE'}
         }

    """
    variables = variables_from_declaration(declaration)
    blocks = collections.defaultdict(dict)

    # Match two groups: (var) := (value)
    # Only works for simple variable assignments.
    arg_value_re = re.compile(r"([a-zA-Z0-9_]+)\s*:=\s*([a-zA-Z0-9_\.]+)")

    for var in variables:
        # Find: ^VAR(.*);
        reg = re.compile(r"^\s*" + var + r"\s*\(\s*((?:.*?\n?)+)\)\s*;", re.MULTILINE)
        for match in reg.findall(implementation):
            call_body = " ".join(line.strip() for line in match.splitlines())
            blocks[var].update(**dict(arg_value_re.findall(call_body)))

    return dict(blocks)
