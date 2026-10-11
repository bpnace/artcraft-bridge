# Contributing

Use Python 3.9 or later. Runtime dependencies are limited to Python's standard library. Changes should remain focused and include tests for behavioral changes.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m recraft_bridge --help
python3 scripts/check_version.py
```

For installed-package checks, create a virtual environment and install the project as described in the README. macOS is required for real desktop launches. CI exercises protocol and lifecycle behavior with synthetic peers; it does not install or operate ArtCraft applications.

When changing an integration, document app version, actual methods exercised, readback results and export formats tested. Use disposable files in a dedicated workspace and separate profiles. Do not perform destructive operations on a contributor's existing projects.

Do not commit runtime state, tokens, credentials, machine-specific paths, application bundles, real customer files or exported media. Tests must use synthetic data. New dependencies, licensing changes, signing changes and broader network access require explicit discussion in the contribution.

Update the README when CLI behavior changes. Follow [VERSIONING.md](VERSIONING.md) for version bumps and [CHANGELOG.md](CHANGELOG.md) for user-visible changes. Submit changes through a pull request and describe verification and remaining limits.
