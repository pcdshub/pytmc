#!/usr/bin/env python3
"""
run_tests.py

Quickly intiate pytest suite. Copied from github repository
pcdshub/transfocate.
"""
import sys

import pytest

if __name__ == "__main__":
    # Show output results from every test function
    # Show the message output for skipped and expected failures
    args = ["-v", "-vrxs", "--color=yes"]

    # Add extra arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    print("pytest arguments: {}".format(args))

sys.exit(pytest.main(args))
