"""Command line: poppy-sidecar generate | validate | testbed"""

import argparse
import json
import sys

from poppy_sidecar import __version__
from poppy_sidecar.generator import generate, interactive_profile, PROFILE_FIELDS
from poppy_sidecar.validator import validate
from poppy_sidecar.testbed import run_testbed


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("error: file not found: %s" % path, file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print("error: invalid JSON in %s: %s" % (path, e), file=sys.stderr)
        sys.exit(2)


def cmd_generate(args):
    if args.interactive:
        profile = interactive_profile()
    else:
        profile = _load_json(args.profile)
    try:
        doc = generate(profile)
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr)
        sys.exit(1)
    out = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print("wrote %s (self-validated against PAP draft 0.1)" % args.output)
    else:
        print(out, end="")


def cmd_validate(args):
    doc = _load_json(args.file)
    report = validate(doc, domain=args.domain, live=args.live)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report)
    if report.errors or (args.strict and report.warnings):
        sys.exit(1)
    sys.exit(0)


def cmd_testbed(args):
    doc = _load_json(args.poppy_json)
    trace = _load_json(args.trace)
    report = run_testbed(doc, trace)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.summary())
    sys.exit(0 if report.passed else 1)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="poppy-sidecar",
        description="First independent developer kit for the Personal Agent Protocol (draft 0.1).")
    ap.add_argument("--version", action="version", version="poppy-sidecar " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="build a poppy.json from a business profile")
    gx = g.add_mutually_exclusive_group(required=True)
    gx.add_argument("--profile", help="business profile JSON file (see below)")
    gx.add_argument("--interactive", action="store_true", help="answer questions on stdin")
    g.add_argument("-o", "--output", help="write poppy.json here (default: stdout)")
    g.set_defaults(func=cmd_generate)

    v = sub.add_parser("validate", help="check a poppy.json for spec compliance")
    v.add_argument("file", help="poppy.json to validate")
    v.add_argument("--domain", help="host the doc was fetched from (domain-match check, §3.1)")
    v.add_argument("--live", action="store_true",
                   help="also check endpoint reachability + OAuth metadata (needs network)")
    v.add_argument("--strict", action="store_true", help="warnings fail too")
    v.add_argument("--json", action="store_true", help="machine-readable output")
    v.set_defaults(func=cmd_validate)

    t = sub.add_parser("testbed", help="check an agent trace against a poppy.json")
    t.add_argument("poppy_json", help="the business's poppy.json")
    t.add_argument("trace", help="agent trace JSON file")
    t.add_argument("--json", action="store_true", help="machine-readable output")
    t.set_defaults(func=cmd_testbed)

    args = ap.parse_args(argv)
    if args.cmd == "generate" and args.profile and args.profile == "HELP":
        print(PROFILE_FIELDS)
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
