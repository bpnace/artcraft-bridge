# Changelog

All changes that affect users are recorded here. Versions follow the policy in [VERSIONING.md](VERSIONING.md).

## [Unreleased]

## [0.1.0] - 2026-10-11

### Added

- Local JSON control bridge for PhotoCraft, DesignCraft, VectorCraft, FilmCraft, LightCraft, EffectCraft, PdfCraft and CADCraft on macOS.
- Inventory, managed launch, state inspection, command discovery, raw method calls and managed shutdown.
- Configurable app, workspace and private state directories through CLI flags and environment variables.
- Authentication for PhotoCraft and PdfCraft, response ID matching, request/reply size limits and one wall-clock transport deadline.
- Process identity validation and a shared lifecycle lock for calls, starts and stops.
- Explicit opt-in for PdfCraft portable bundle copying/signing and for empty-session signal termination.
- Params-file input, installable CLI, semantic version policy and automated tests.

### Verification

- The original local bridge was exercised against all eight installed apps. DesignCraft document creation, text insertion, save, readback and PNG render were verified.
- This repository's reproducible automated tests and current manual evidence are documented in [docs/verification.md](docs/verification.md).

### Limitations

- Experimental macOS support. Other platforms and all individual app commands have not been verified.
- No registered MCP server, hosted API, bundled ArtCraft apps or automatic graphical-session attachment.
