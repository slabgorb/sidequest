#!/usr/bin/env python3
"""
check.py - Quality gate runner for pre-handoff verification

Story 21-1: /check command with dev-handoff integration

Usage: python check.py [OPTIONS]

Options:
    --skip-check       Skip all checks (emergency bypass)
    --tests-only       Run only tests, skip lint and typecheck
    --filter PATTERN   Filter tests by pattern (passed to test runner)
    --repo REPO        Run checks in specific repo subdirectory
    --no-lint          Skip lint check
    --no-typecheck     Skip type check
    --fast             Skip slow packages (cyclist/Electron) for rapid iteration

Runs lint, type check, and tests concurrently. Reports pass/fail status.
Returns exit code 0 on all passing, non-zero on any failure.
"""

import argparse
import asyncio
import json
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    command: str | None = None
    message: str | None = None


@dataclass
class CheckStats:
    run: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0

    def record(self, status: CheckStatus) -> None:
        if status == CheckStatus.PASS:
            self.run += 1
            self.passed += 1
        elif status == CheckStatus.FAIL:
            self.run += 1
            self.failed += 1
        elif status == CheckStatus.SKIP:
            self.skipped += 1


@dataclass
class RepoConfig:
    path: str = ""
    lint_cmd: str = ""
    test_cmd: str = ""
    test_filter_flag: str = ""
    language: str = ""


@dataclass
class CheckContext:
    project_root: Path
    working_dir: Path
    target_repo: str = ""
    test_filter: str = ""
    no_lint: bool = False
    no_typecheck: bool = False
    fast_mode: bool = False
    repo_config: RepoConfig = field(default_factory=RepoConfig)
    stats: CheckStats = field(default_factory=CheckStats)


# ANSI colors
class Colors:
    def __init__(self, enabled: bool = True):
        if enabled and sys.stdout.isatty():
            self.RED = "\033[0;31m"
            self.GREEN = "\033[0;32m"
            self.YELLOW = "\033[0;33m"
            self.CYAN = "\033[0;36m"
            self.NC = "\033[0m"
        else:
            self.RED = ""
            self.GREEN = ""
            self.YELLOW = ""
            self.CYAN = ""
            self.NC = ""


COLORS = Colors()


def print_pass(name: str, command: str | None = None) -> None:
    suffix = f" ({command})" if command else ""
    print(f"  {COLORS.GREEN}[PASS]{COLORS.NC} {name}{suffix}")


def print_fail(name: str, command: str | None = None) -> None:
    suffix = f" ({command})" if command else ""
    print(f"  {COLORS.RED}[FAIL]{COLORS.NC} {name}{suffix}")


def print_skip(name: str, reason: str = "") -> None:
    suffix = f" - {reason}" if reason else ""
    print(f"  {COLORS.YELLOW}[SKIP]{COLORS.NC} {name}{suffix}")


def print_section(title: str) -> None:
    print()
    print(f"{COLORS.CYAN}{title}{COLORS.NC}")
    print("=" * 40)


def find_project_root() -> Path:
    """Find project root by looking for .pennyfarthing directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".pennyfarthing").is_dir():
            return current
        current = current.parent
    return Path.cwd()


def detect_project_type(working_dir: Path) -> str:
    """Detect project type based on files present."""
    if (working_dir / "package.json").exists():
        return "node"

    # Check for Go files
    go_files = list(working_dir.glob("*.go"))
    if go_files:
        return "go"

    if (working_dir / "go.mod").exists():
        return "go"

    return "unknown"


def has_just_recipe(recipe: str, working_dir: Path) -> bool:
    """Check if justfile has a specific recipe."""
    if not (working_dir / "justfile").exists():
        return False
    if not shutil.which("just"):
        return False

    try:
        import subprocess
        result = subprocess.run(
            ["just", "--list"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=5
        )
        return any(line.startswith(f"{recipe} ") or line.strip() == recipe
                   for line in result.stdout.splitlines())
    except Exception:
        return False


def has_npm_script(script: str, working_dir: Path) -> bool:
    """Check if package.json has a specific script."""
    package_json = working_dir / "package.json"
    if not package_json.exists():
        return False

    try:
        with open(package_json) as f:
            data = json.load(f)
        return script in data.get("scripts", {})
    except Exception:
        return False


async def run_command(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    """Run a command asynchronously and return (success, output)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        output = stdout.decode() + stderr.decode()
        return success, output
    except Exception as e:
        return False, str(e)


async def run_shell_command(cmd: str, cwd: Path) -> tuple[bool, str]:
    """Run a shell command asynchronously."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        output = stdout.decode() + stderr.decode()
        return success, output
    except Exception as e:
        return False, str(e)


async def run_lint(ctx: CheckContext) -> CheckResult:
    """Run lint check."""
    if ctx.no_lint:
        return CheckResult("Lint", CheckStatus.SKIP, message="skipped by --no-lint or --tests-only")

    working_dir = ctx.working_dir

    # Use repo config lint command if available
    if ctx.repo_config.lint_cmd:
        success, _ = await run_shell_command(ctx.repo_config.lint_cmd, working_dir)
        return CheckResult(
            "Lint",
            CheckStatus.PASS if success else CheckStatus.FAIL,
            command=ctx.repo_config.lint_cmd
        )

    # Prefer justfile recipes
    if has_just_recipe("lint", working_dir):
        success, _ = await run_command(["just", "lint"], working_dir)
        return CheckResult("Lint", CheckStatus.PASS if success else CheckStatus.FAIL, command="just lint")

    project_type = detect_project_type(working_dir)

    if project_type == "node" and has_npm_script("lint", working_dir):
        success, _ = await run_command(["npm", "run", "lint"], working_dir)
        return CheckResult("Lint", CheckStatus.PASS if success else CheckStatus.FAIL, command="npm run lint")

    if project_type == "go" and shutil.which("golangci-lint"):
        success, _ = await run_command(["golangci-lint", "run"], working_dir)
        return CheckResult("Lint", CheckStatus.PASS if success else CheckStatus.FAIL, command="golangci-lint")

    eslint_path = working_dir / "node_modules" / ".bin" / "eslint"
    if eslint_path.exists():
        success, _ = await run_command([str(eslint_path), "."], working_dir)
        return CheckResult("Lint", CheckStatus.PASS if success else CheckStatus.FAIL, command="eslint")

    return CheckResult("Lint", CheckStatus.SKIP, message="no lint command configured")


async def run_typecheck(ctx: CheckContext) -> CheckResult:
    """Run type check."""
    if ctx.no_typecheck:
        return CheckResult("Type Check", CheckStatus.SKIP, message="skipped by --no-typecheck or --tests-only")

    working_dir = ctx.working_dir

    # Prefer justfile recipes
    if has_just_recipe("typecheck", working_dir):
        success, _ = await run_command(["just", "typecheck"], working_dir)
        return CheckResult("Type Check", CheckStatus.PASS if success else CheckStatus.FAIL, command="just typecheck")

    has_tsconfig = (working_dir / "tsconfig.json").exists()

    if has_tsconfig and has_npm_script("typecheck", working_dir):
        success, _ = await run_command(["npm", "run", "typecheck"], working_dir)
        return CheckResult("Type Check", CheckStatus.PASS if success else CheckStatus.FAIL, command="npm run typecheck")

    if has_tsconfig and shutil.which("tsc"):
        success, _ = await run_command(["tsc", "--noEmit"], working_dir)
        return CheckResult("Type Check", CheckStatus.PASS if success else CheckStatus.FAIL, command="tsc --noEmit")

    tsc_path = working_dir / "node_modules" / ".bin" / "tsc"
    if has_tsconfig and tsc_path.exists():
        success, _ = await run_command([str(tsc_path), "--noEmit"], working_dir)
        return CheckResult("Type Check", CheckStatus.PASS if success else CheckStatus.FAIL, command="tsc --noEmit")

    if has_tsconfig:
        return CheckResult("Type Check", CheckStatus.SKIP, message="TypeScript found but no typecheck command")

    return CheckResult("Type Check", CheckStatus.SKIP, message="not a TypeScript project")


async def run_tests(ctx: CheckContext) -> CheckResult:
    """Run tests."""
    working_dir = ctx.working_dir
    test_filter = ctx.test_filter

    if test_filter:
        print(f"  Filter: {test_filter}")

    # Use repo config test command if available
    if ctx.repo_config.test_cmd:
        cmd = ctx.repo_config.test_cmd
        if test_filter and ctx.repo_config.test_filter_flag:
            cmd = f'{cmd} {ctx.repo_config.test_filter_flag} "{test_filter}"'
        success, _ = await run_shell_command(cmd, working_dir)
        label = ctx.repo_config.test_cmd
        if test_filter:
            label += f" {ctx.repo_config.test_filter_flag} {test_filter}"
        return CheckResult("Tests", CheckStatus.PASS if success else CheckStatus.FAIL, command=label)

    # Prefer justfile recipes
    if has_just_recipe("test", working_dir):
        cmd = ["just", "test"]
        label = "just test"
        if test_filter:
            cmd.append(test_filter)
            label += f" {test_filter}"
        success, _ = await run_command(cmd, working_dir)
        return CheckResult("Tests", CheckStatus.PASS if success else CheckStatus.FAIL, command=label)

    project_type = detect_project_type(working_dir)

    if project_type == "node" and has_npm_script("test", working_dir):
        # Check for pnpm workspace (monorepo)
        pnpm_workspace = (working_dir / "pnpm-workspace.yaml").exists()
        has_pnpm = shutil.which("pnpm") is not None

        if pnpm_workspace and has_pnpm:
            if ctx.fast_mode:
                cmd = "pnpm -r --filter '!@pennyfarthing/cyclist' test"
                label = "pnpm test (fast mode - skipping cyclist)"
            else:
                cmd = "pnpm -r test"
                label = "pnpm test"
        else:
            cmd = "npm test"
            label = "npm test"

        if test_filter:
            cmd += f' -- -t "{test_filter}"'
            label += f" -t {test_filter}"

        success, _ = await run_shell_command(cmd, working_dir)
        return CheckResult("Tests", CheckStatus.PASS if success else CheckStatus.FAIL, command=label)

    if project_type == "go":
        cmd = "go test ./..."
        label = "go test ./..."
        if test_filter:
            cmd = f'go test -run "{test_filter}" ./...'
            label = f"go test -run {test_filter} ./..."
        success, _ = await run_shell_command(cmd, working_dir)
        return CheckResult("Tests", CheckStatus.PASS if success else CheckStatus.FAIL, command=label)

    jest_path = working_dir / "node_modules" / ".bin" / "jest"
    if jest_path.exists():
        cmd = [str(jest_path)]
        label = "jest"
        if test_filter:
            cmd.extend(["-t", test_filter])
            label += f" -t {test_filter}"
        success, _ = await run_command(cmd, working_dir)
        return CheckResult("Tests", CheckStatus.PASS if success else CheckStatus.FAIL, command=label)

    return CheckResult("Tests", CheckStatus.SKIP, message="no test command configured")


def print_result(result: CheckResult, stats: CheckStats) -> None:
    """Print a check result and update stats."""
    stats.record(result.status)

    if result.status == CheckStatus.PASS:
        print_pass(result.name, result.command)
    elif result.status == CheckStatus.FAIL:
        print_fail(result.name, result.command)
    else:
        print_skip(result.name, result.message or "")


def print_summary(stats: CheckStats, project_type: str) -> int:
    """Print summary and return exit code."""
    print_section("Summary")
    print()
    print(f"Checks run:    {stats.run}")
    print(f"Checks passed: {COLORS.GREEN}{stats.passed}{COLORS.NC}")

    if stats.failed > 0:
        print(f"Checks failed: {COLORS.RED}{stats.failed}{COLORS.NC}")
    else:
        print(f"Checks failed: {stats.failed}")

    if stats.skipped > 0:
        print(f"Checks skipped: {COLORS.YELLOW}{stats.skipped}{COLORS.NC}")

    print()

    if stats.failed > 0:
        print(f"{COLORS.RED}FAILED{COLORS.NC} - {stats.failed} check(s) failed")
        print("Fix issues before handoff to Reviewer.")
        return 1
    elif stats.run == 0:
        print(f"{COLORS.YELLOW}WARNING{COLORS.NC} - No checks ran (project type: {project_type})")
        print("Consider adding lint/test scripts to package.json or justfile.")
        return 0
    else:
        print(f"{COLORS.GREEN}PASSED{COLORS.NC} - All checks passed")
        return 0


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quality gate runner for pre-handoff verification"
    )
    parser.add_argument("--skip-check", action="store_true",
                        help="Skip all checks (emergency bypass)")
    parser.add_argument("--tests-only", action="store_true",
                        help="Run only tests, skip lint and typecheck")
    parser.add_argument("--filter", dest="test_filter", default="",
                        help="Filter tests by pattern")
    parser.add_argument("--repo", dest="target_repo", default="",
                        help="Run checks in specific repo subdirectory")
    parser.add_argument("--no-lint", action="store_true",
                        help="Skip lint check")
    parser.add_argument("--no-typecheck", action="store_true",
                        help="Skip type check")
    parser.add_argument("--fast", action="store_true",
                        help="Skip slow packages for rapid iteration")

    args = parser.parse_args()

    # Handle --skip-check
    if args.skip_check:
        print("Quality checks skipped by --skip-check flag")
        print()
        print("WARNING: Skipping checks is for emergencies only.")
        print("Ensure checks pass before merging PR.")
        return 0

    # Handle --tests-only
    no_lint = args.no_lint or args.tests_only
    no_typecheck = args.no_typecheck or args.tests_only

    # Find project root
    project_root = find_project_root()

    # Handle --repo
    if args.target_repo:
        working_dir = project_root / args.target_repo
        if not working_dir.is_dir():
            print(f"Error: Repo directory not found: {working_dir}")
            return 1
    else:
        working_dir = project_root

    # Create context
    ctx = CheckContext(
        project_root=project_root,
        working_dir=working_dir,
        target_repo=args.target_repo,
        test_filter=args.test_filter,
        no_lint=no_lint,
        no_typecheck=no_typecheck,
        fast_mode=args.fast
    )

    # Print header
    print()
    print("Quality Gate Check")
    print("==================")
    print(f"Project: {project_root}")
    if args.target_repo:
        print(f"Repo: {args.target_repo}")
    print(f"Working dir: {working_dir}")
    if args.fast:
        print(f"{COLORS.YELLOW}Mode: FAST (skipping slow packages){COLORS.NC}")

    project_type = detect_project_type(working_dir)

    # Run lint and typecheck concurrently, then tests
    # (Tests often depend on lint/typecheck passing in CI, but we run all for reporting)
    print_section("Lint")
    lint_result = await run_lint(ctx)
    print_result(lint_result, ctx.stats)

    print_section("Type Check")
    typecheck_result = await run_typecheck(ctx)
    print_result(typecheck_result, ctx.stats)

    print_section("Tests")
    test_result = await run_tests(ctx)
    print_result(test_result, ctx.stats)

    return print_summary(ctx.stats, project_type)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
