<gate name="release-ready" model="haiku">

<purpose>
Composite gate for pre-deploy verification. Extends tests-pass with build,
version, and changelog checks. Extracts the pre-deploy checklist from devops.md.
</purpose>

<ref gate="gates/tests-pass" />

<check name="build-succeeds">
Build completes without errors.
Run `cd pennyfarthing && pnpm build`. Exit code 0 = pass.
</check>

<check name="version-bumped">
Package version has been incremented.
Compare current `package.json` version against latest git tag
(`git describe --tags --abbrev=0`). Current must be strictly greater.
</check>

<check name="changelog-updated">
CHANGELOG.md has an entry for the new version.
Grep `CHANGELOG.md` for the current package.json version string.
</check>

<check name="changelog-links-valid">
CHANGELOG.md comparison links are correct.
Run `pennyfarthing-dist/scripts/git/changelog-links.sh --validate`. Exit code 0 = pass.
</check>

<check name="e2e-consumer-tests">
Consumer E2E test suite passes. Tests pf init, Frame startup,
content preservation, and idempotency in isolated environments.
Run `./tests/e2e/run.sh --local`. Exit code 0 = pass.
</check>

<pass>
Run all checks from `gates/tests-pass` (test-suite, working-tree, branch-status),
then run build-succeeds, version-bumped, changelog-updated, and changelog-links-valid.

If ALL pass, return:

```yaml
GATE_RESULT:
  status: pass
  gate: release-ready
  message: "Release ready: v{version}. Tests green, build clean, changelog updated."
  checks:
    - name: test-suite
      status: pass
      detail: "{passed}/{total} tests passing"
    - name: working-tree
      status: pass
      detail: "No uncommitted changes"
    - name: branch-status
      status: pass
      detail: "On branch {branch}"
    - name: build-succeeds
      status: pass
      detail: "Build completed successfully"
    - name: version-bumped
      status: pass
      detail: "v{version} > v{tag}"
    - name: changelog-updated
      status: pass
      detail: "CHANGELOG.md has entry for v{version}"
    - name: changelog-links-valid
      status: pass
      detail: "Comparison links correct ({count} versions)"
    - name: e2e-consumer-tests
      status: pass
      detail: "6/6 consumer E2E scenarios passed"
```
</pass>

<fail>
If ANY check fails, report all results:

```yaml
GATE_RESULT:
  status: fail
  gate: release-ready
  message: "Not release ready: {summary}"
  checks:
    - name: test-suite
      status: pass | fail
      detail: "{test results or failure list}"
    - name: working-tree
      status: pass | fail
      detail: "{clean or list of uncommitted files}"
    - name: branch-status
      status: pass | fail
      detail: "{branch info}"
    - name: build-succeeds
      status: pass | fail
      detail: "{build status or error summary}"
    - name: version-bumped
      status: pass | fail
      detail: "{version comparison or same-version warning}"
    - name: changelog-updated
      status: pass | fail
      detail: "{changelog status}"
    - name: changelog-links-valid
      status: pass | fail
      detail: "{link validation result}"
  recovery:
    - "Fix failing tests before release"
    - "Commit or stash uncommitted changes"
    - "Resolve build errors"
    - "Run: npm version patch|minor|major"
    - "Add changelog entry for v{version}"
    - "Run: pennyfarthing-dist/scripts/git/changelog-links.sh --fix"
    - "Run: ./tests/e2e/run.sh --local (if e2e-consumer-tests fails)"
```
</fail>

</gate>
