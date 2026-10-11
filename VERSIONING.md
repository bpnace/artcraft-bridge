# Versioning and releases

The initial version is **0.1.0**. It is experimental. This repository uses `MAJOR.MINOR.PATCH` version numbers.

## Policy

- During `0.x`, incompatible CLI, Python API or session-state changes increase the minor version. Bug fixes that keep compatibility increase the patch version.
- From `1.0.0`, incompatible changes increase the major version, compatible features increase the minor version, and compatible fixes increase the patch version.
- Each release records supported app versions and any required session-state migration. App releases are independent of bridge releases; an app upgrade can change available methods and command schemas.
- Prereleases use suffixes such as `0.2.0-rc.1` in Git tags and changelog entries. Python package prerelease spelling must follow Python packaging conventions before a prerelease package is built.

## Source of truth

The package version is `src/recraft_bridge/__init__.py`. `pyproject.toml` obtains package metadata dynamically from it. The `VERSION` file and versioned changelog heading must match. Check with

```sh
python3 scripts/check_version.py
```

Git tags are `vMAJOR.MINOR.PATCH`, for example `v0.1.0`. A version file or changelog entry does not prove that a GitHub release or package registry publication exists.

## Release procedure

1. Update the package version, `VERSION` and `CHANGELOG.md` together.
2. Run the automated tests, CLI smoke checks and version consistency check.
3. Exercise affected app integrations on macOS using disposable documents and separate profiles. Record app versions and what was actually verified.
4. Review the exact outgoing files and commits for secrets, personal paths, runtime state, generated documents and third-party assets.
5. Build wheel and source distribution and inspect their contents. Do not bundle runtime profiles, app binaries, control files or tokens.
6. Commit the reviewed changes and tag that exact commit. Publish only the reviewed refs and artifacts, using the maintainer's publication approval process.
7. Verify the public repository, tag and downloadable artifacts from an anonymous session.

A future automated release workflow should enforce these steps. Version 0.1.0 has no automatic PyPI or GitHub release publishing job.
