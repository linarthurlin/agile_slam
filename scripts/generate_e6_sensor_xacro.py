#!/usr/bin/env python3
"""Generate an e6 sensor-frame Xacro include after inventory and calibration pass."""
import argparse
from pathlib import Path
import sys

from e6_profile import load_profile, render_sensor_xacro


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path,
                        help="destination for the generated Xacro include")
    parser.add_argument("--force", action="store_true", help="replace an existing generated file")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"Refusing to overwrite existing file: {args.output} (pass --force to replace it).", file=sys.stderr)
        return 2
    try:
        inventory, calibration, driver_matrix = load_profile()
        xml = render_sensor_xacro(inventory, calibration, driver_matrix)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(xml, encoding="utf-8", newline="\n")
    print(f"Generated calibrated sensor-frame include: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
