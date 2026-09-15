"""fit_srm: part of the synthetic parasol kernel-shortening project (fixture S3).

This file exists so the Script node has a real path and hash. It is not run.
"""

import sys


def main(argv: list[str]) -> int:
    print("fit_srm: fixture script, nothing to do", argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
