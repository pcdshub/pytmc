"""Tool for making XML-formatted files human-readable

Output uses the following rules:
For a line of xml that appears as the following:
<tag attr=qual...> text </tag> tail

Note that tail takes precedence over text.

This program will output the following:
{attrs:qual...} tag text tail

Tags contained by other tags are indented and printed on the following line.

This tool was created for exploring .tpy files but is well suited to reading
any xml formatted file.
"""

import xml.etree.ElementTree as ET
import textwrap
import argparse


DESCRIPTION = __doc__


def build_arg_parser(parser=None):
    if parser is None:
        parser = argparse.ArgumentParser()

    parser.description = DESCRIPTION
    parser.formatter_class = argparse.RawTextHelpFormatter

    parser.add_argument(
        'input_file', type=str, help='input file'
    )

    parser.add_argument(
        '-d', '--depth', type=int,
        help='Recursive limit for exploring the file',
        default=7
    )

    parser.add_argument(
        '-i', '--indent_size',
        type=int, help='Indent size for output formatting',
        default=4
    )

    return parser


def recursive(branch, level=1, indent_size=4, indent=0):
    if branch is None:
        return
    if level == 0:
        return
    for limb in branch:
        # for i in range(indent):
        #    print("    ",end="")
        print(
            textwrap.indent(
                " ".join([
                    str(limb.attrib),
                    str(limb.tag),
                    str(limb.text),
                    str(limb.tail)
                ]),
                "".join([" "]*indent_size*indent)
            )
        )
        recursive(limb, level-1, indent_size, indent+1)


def main(input_file, *, indent_size=4, depth=7):
    tree = ET.parse(input_file)
    root = tree.getroot()
    recursive(root, depth, indent_size)
