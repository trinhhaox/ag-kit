#!/usr/bin/env python3
"""
Master Checklist Runner - Antigravity Kit
==========================================

Orchestrates all validation scripts in priority order.
Use this for incremental validation during development.

Usage:
    python3 scripts/checklist.py .                    # Run core checks (parallel)
    python3 scripts/checklist.py . --url <URL>        # Include performance checks
    python3 scripts/checklist.py . -j 1               # Sequential, stop on critical failure
    python3 scripts/checklist.py . --json             # Machine-readable report

Priority Order:
    P0: Security Scan (vulnerabilities, secrets)
    P1: Lint & Type Check (code quality)
    P2: Schema Validation (if database exists)
    P3: Test Runner (unit/integration tests)
    P4: UX Audit (psychology laws, accessibility)
    P5: SEO Check (meta tags, structure)
    P6: Performance (lighthouse - requires URL)
"""

import argparse
import contextlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_runner import Check, default_jobs, print_error, print_header, run_checks, summarize  # noqa: E402

CHECKS = [
    Check("Security Scan", "skills/vulnerability-scanner/scripts/security_scan.py", True, "Core"),
    Check("Lint Check", "skills/lint-and-validate/scripts/lint_runner.py", True, "Core"),
    Check("Schema Validation", "skills/database-design/scripts/schema_validator.py", False, "Core"),
    Check("Test Runner", "skills/testing-patterns/scripts/test_runner.py", False, "Core"),
    Check("UX Audit", "skills/frontend-design/scripts/ux_audit.py", False, "Core"),
    Check("SEO Check", "skills/seo-fundamentals/scripts/seo_checker.py", False, "Core"),
    Check("Lighthouse Audit", "skills/performance-profiling/scripts/lighthouse_audit.py", True, "Performance", True),
    Check("Playwright E2E", "skills/webapp-testing/scripts/playwright_runner.py", False, "Performance", True),
]


def main():
    parser = argparse.ArgumentParser(
        description="Run Antigravity Kit validation checklist",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/checklist.py .                                  # Core checks only
  python3 scripts/checklist.py . --url http://localhost:3000      # Include performance
        """,
    )
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument("--url", help="URL for performance checks (lighthouse, playwright)")
    parser.add_argument("--skip-performance", action="store_true", help="Skip performance checks even if URL provided")
    parser.add_argument("-j", "--jobs", type=int, default=default_jobs(),
                        help="Parallel workers (default: %(default)s; 1 = sequential and stop on critical failure)")
    parser.add_argument("--timeout", type=int, default=300, help="Per-check timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print a JSON report (progress goes to stderr)")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.exists():
        print_error(f"Project path does not exist: {project}")
        sys.exit(1)

    url = None if args.skip_performance else args.url
    out = contextlib.redirect_stdout(sys.stderr) if args.json else contextlib.nullcontext()
    start = time.monotonic()
    with out:
        print_header("🚀 ANTIGRAVITY KIT - MASTER CHECKLIST")
        print(f"Project: {project}")
        print(f"URL: {url or 'Not provided (performance checks skipped)'}")
        results = run_checks(CHECKS, project, url, args.jobs, args.timeout, stop_on_required_fail=True)

    ok = summarize(results, time.monotonic() - start, as_json=args.json)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
