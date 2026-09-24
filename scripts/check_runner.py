#!/usr/bin/env python3
"""
Shared check runner for checklist.py and verify_all.py.

- Resolves validation scripts relative to the kit itself (works whether the kit
  is symlinked as `.agent/` or run from its own checkout).
- Runs independent checks in parallel (thread pool around subprocesses) and
  prints results in their declared priority order.
- Uses the current interpreter (sys.executable) instead of a bare `python`,
  which does not exist on many systems.
"""

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

KIT_DIR = Path(__file__).resolve().parent.parent


class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    @classmethod
    def disable(cls):
        for name in ("BLUE", "CYAN", "GREEN", "YELLOW", "RED", "ENDC", "BOLD"):
            setattr(cls, name, "")


if not sys.stdout.isatty():
    Colors.disable()


def print_header(text: str, width: int = 60):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * width}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(width)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * width}{Colors.ENDC}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")


def print_error(text: str):
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")


@dataclass
class Check:
    name: str
    script: str            # path relative to the kit root, e.g. "skills/x/scripts/y.py"
    required: bool = False
    category: str = ""
    needs_url: bool = False


@dataclass
class Result:
    name: str
    category: str
    required: bool
    passed: bool = True
    skipped: bool = False
    duration: float = 0.0
    output: str = ""
    error: str = ""
    reason: str = field(default="")


def resolve_script(script: str, project: Path) -> Optional[Path]:
    """Find a check script in the kit, falling back to <project>/.agent/."""
    for base in (KIT_DIR, project / ".agent"):
        candidate = base / script
        if candidate.is_file():
            return candidate
    return None


def run_check(check: Check, project: Path, url: Optional[str], timeout: int) -> Result:
    result = Result(name=check.name, category=check.category, required=check.required)
    script = resolve_script(check.script, project)
    if script is None:
        result.skipped, result.reason = True, "script not found"
        return result

    cmd = [sys.executable, str(script), str(project)]
    if url and check.needs_url:
        cmd.append(url)

    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(project))
        result.passed = proc.returncode == 0
        result.output, result.error = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        result.passed, result.error = False, f"Timeout (>{timeout}s)"
    except OSError as e:
        result.passed, result.error = False, str(e)
    result.duration = time.monotonic() - start
    return result


def report_line(r: Result) -> None:
    if r.skipped:
        print_warning(f"{r.name}: skipped ({r.reason})")
    elif r.passed:
        print_success(f"{r.name}: PASSED ({r.duration:.1f}s)")
    else:
        print_error(f"{r.name}: FAILED ({r.duration:.1f}s)")
        detail = (r.error or r.output).strip()
        if detail:
            print(f"   {detail[:300]}")


def run_checks(checks: List[Check], project: Path, url: Optional[str], jobs: int,
               timeout: int, stop_on_required_fail: bool) -> List[Result]:
    """Run checks; parallel when jobs > 1. Results keep the declared order."""
    checks = [c for c in checks if url or not c.needs_url]
    results: List[Result] = []

    if jobs <= 1:
        current = None
        for check in checks:
            if check.category != current:
                current = check.category
                print_header(f"📋 {current.upper()}")
            r = run_check(check, project, url, timeout)
            report_line(r)
            results.append(r)
            if stop_on_required_fail and r.required and not r.passed and not r.skipped:
                print_error(f"CRITICAL: {r.name} failed. Stopping.")
                break
        return results

    print(f"Running {len(checks)} checks with {jobs} parallel workers...\n")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = [pool.submit(run_check, c, project, url, timeout) for c in checks]
        current = None
        for future in futures:  # print in priority order as results become available
            r = future.result()
            if r.category != current:
                current = r.category
                print(f"\n{Colors.BOLD}{Colors.CYAN}{current}{Colors.ENDC}")
            report_line(r)
            results.append(r)
    return results


def summarize(results: List[Result], total_duration: float, as_json: bool = False) -> bool:
    passed = sum(1 for r in results if r.passed and not r.skipped)
    failed = [r for r in results if not r.passed and not r.skipped]
    skipped = sum(1 for r in results if r.skipped)

    if as_json:
        print(json.dumps({
            "passed": passed,
            "failed": len(failed),
            "skipped": skipped,
            "duration": round(total_duration, 2),
            "results": [asdict(r) for r in results],
        }, indent=2))
        return not failed

    print_header("📊 SUMMARY")
    print(f"Total Duration: {total_duration:.1f}s")
    print(f"Total Checks: {len(results)}")
    print(f"{Colors.GREEN}✅ Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.RED}❌ Failed: {len(failed)}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⏭️  Skipped: {skipped}{Colors.ENDC}\n")

    if failed:
        critical = [r.name for r in failed if r.required]
        if critical:
            print_error(f"Critical failures: {', '.join(critical)}")
        print_error(f"{len(failed)} check(s) FAILED - fix critical (security, lint) issues first")
        return False
    print_success("All checks PASSED ✨")
    return True


def default_jobs() -> int:
    import os
    return max(1, min(4, os.cpu_count() or 1))
