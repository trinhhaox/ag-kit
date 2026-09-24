#!/usr/bin/env python3
"""
Full Verification Suite - Antigravity Kit
==========================================

Runs COMPLETE validation including all checks + performance + E2E.
Use this before deployment or major releases.

Usage:
    python3 scripts/verify_all.py . --url <URL>
    python3 scripts/verify_all.py .                    # Static checks only
    python3 scripts/verify_all.py . --url <URL> --json

Includes ALL checks:
    ✅ Security Scan (OWASP, secrets, dependencies)
    ✅ Lint & Type Coverage
    ✅ Schema Validation
    ✅ Test Suite (unit + integration)
    ✅ UX Audit (psychology, accessibility)
    ✅ SEO / GEO Check
    ✅ Lighthouse (Core Web Vitals)       - requires --url
    ✅ Playwright E2E                     - requires --url
    ✅ Mobile Audit (if applicable)
    ✅ i18n Check
"""

import argparse
import contextlib
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_runner import Check, default_jobs, print_error, print_header, run_checks, summarize  # noqa: E402

SUITE = [
    # P0: Security (CRITICAL)
    Check("Security Scan", "skills/vulnerability-scanner/scripts/security_scan.py", True, "Security"),
    # P1: Code Quality (CRITICAL)
    Check("Lint Check", "skills/lint-and-validate/scripts/lint_runner.py", True, "Code Quality"),
    Check("Type Coverage", "skills/lint-and-validate/scripts/type_coverage.py", False, "Code Quality"),
    # P2: Data Layer
    Check("Schema Validation", "skills/database-design/scripts/schema_validator.py", False, "Data Layer"),
    # P3: Testing
    Check("Test Suite", "skills/testing-patterns/scripts/test_runner.py", False, "Testing"),
    # P4: UX & Accessibility
    Check("UX Audit", "skills/frontend-design/scripts/ux_audit.py", False, "UX & Accessibility"),
    Check("Accessibility Check", "skills/frontend-design/scripts/accessibility_checker.py", False, "UX & Accessibility"),
    # P5: SEO & Content
    Check("SEO Check", "skills/seo-fundamentals/scripts/seo_checker.py", False, "SEO & Content"),
    Check("GEO Check", "skills/geo-fundamentals/scripts/geo_checker.py", False, "SEO & Content"),
    # P6: Performance (requires URL)
    Check("Lighthouse Audit", "skills/performance-profiling/scripts/lighthouse_audit.py", True, "Performance", True),
    # P7: E2E Testing (requires URL)
    Check("Playwright E2E", "skills/webapp-testing/scripts/playwright_runner.py", False, "E2E Testing", True),
    # P8: Mobile
    Check("Mobile Audit", "skills/mobile-design/scripts/mobile_audit.py", False, "Mobile"),
    # P9: Internationalization
    Check("i18n Check", "skills/i18n-localization/scripts/i18n_checker.py", False, "Internationalization"),
]


def main():
    parser = argparse.ArgumentParser(
        description="Run complete Antigravity Kit verification suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/verify_all.py . --url http://localhost:3000
  python3 scripts/verify_all.py . --url https://staging.example.com --no-e2e
        """,
    )
    parser.add_argument("project", help="Project path to validate")
    parser.add_argument("--url", help="URL for performance & E2E checks (skipped when omitted)")
    parser.add_argument("--no-e2e", action="store_true", help="Skip E2E tests")
    parser.add_argument("--stop-on-fail", action="store_true",
                        help="Stop on first critical failure (implies sequential run)")
    parser.add_argument("-j", "--jobs", type=int, default=default_jobs(), help="Parallel workers (default: %(default)s)")
    parser.add_argument("--timeout", type=int, default=600, help="Per-check timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Print a JSON report (progress goes to stderr)")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.exists():
        print_error(f"Project path does not exist: {project}")
        sys.exit(1)

    checks = [c for c in SUITE if not (args.no_e2e and c.category == "E2E Testing")]
    jobs = 1 if args.stop_on_fail else args.jobs
    out = contextlib.redirect_stdout(sys.stderr) if args.json else contextlib.nullcontext()
    start = time.monotonic()
    with out:
        print_header("🚀 ANTIGRAVITY KIT - FULL VERIFICATION SUITE", 70)
        print(f"Project: {project}")
        print(f"URL: {args.url or 'Not provided (performance & E2E skipped)'}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        results = run_checks(checks, project, args.url, jobs, args.timeout, stop_on_required_fail=args.stop_on_fail)

    ok = summarize(results, time.monotonic() - start, as_json=args.json)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
