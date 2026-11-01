#!/usr/bin/env python3
"""Validate the GEM e6 sensor inventory, TF contract, and readiness gates."""
import argparse
import sys

from e6_profile import load_profile, inspect_profile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-ready", action="store_true",
                        help="return a failure unless inventory, calibration, drivers, clocks, and bandwidth are validated")
    parser.add_argument("--verbose", action="store_true", help="list individual pending readiness items")
    args = parser.parse_args(argv)
    inventory, calibration, driver_matrix = load_profile()
    report = inspect_profile(inventory, calibration, driver_matrix)
    if report.contract_errors:
        for error in report.contract_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("E6 inventory and TF/topic contract: structurally valid.")
    if report.calibration_issues:
        print(f"Calibration readiness: pending ({len(report.calibration_issues)} items).")
        if args.verbose:
            for issue in report.calibration_issues:
                print(f"  - {issue}")
    else:
        print("Calibration readiness: validated.")
    if report.integration_issues:
        print(f"Driver/clock/bandwidth readiness: pending ({len(report.integration_issues)} items).")
        if args.verbose:
            for issue in report.integration_issues:
                print(f"  - {issue}")
    else:
        print("Driver/clock/bandwidth readiness: validated.")
    if not args.verbose and (report.calibration_issues or report.integration_issues):
        print("Run with --verbose to list each pending item.")
    if args.require_ready and not report.integration_ready:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
