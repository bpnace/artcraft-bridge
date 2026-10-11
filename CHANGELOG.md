# Changelog

All changes that affect users are recorded here. Versions follow the policy in [VERSIONING.md](VERSIONING.md).

## [0.6.0] - 2026-10-11

### Added

- PhotoCraft `app.open` canonical-path reuse and saved-only explicit reload, using the existing document-operation lock.
- PdfCraft `ui.open` path reuse, verified inactive-tab activation and refusal of ambiguous UI state. PDF reload remains unsupported.
- VectorCraft canonical-path reuse for `app.open` and path-based `document.open`, with serialized tab discovery and fail-closed handling of unknown paths.
- `open-document` support for PhotoCraft, PdfCraft and VectorCraft; regression tests and six-app live reuse evidence.

### Verified limitations

- VectorCraft managed path reuse verified live after a user-authorized regular restart: two saved documents restored, three repeated opens from an inactive tab, zero duplicates. An ordinary GUI session cannot enable its control listener after startup.
- VectorCraft refuses a new open if a pathless tab prevents proving that the file is not already open. Save pathless documents before a new guarded open; select an existing tab directly to continue editing it.
- Native calls and repeated document creation bypass opening guards. FilmCraft/EffectCraft reload tests cover saved projects only.


## [0.5.0] - 2026-10-11

### Changed

- CADCraft `call app.open` activates an already-open canonical file path instead of adding another tab. This changes open semantics, so the experimental minor version is increased.
- CAD examples explicitly reload saved files, closing saved matching tabs before reopening. Dirty matching documents prevent reload.

### Added

- `open-document cadcraft PATH [--reload]`, raw `call ... --reload-document` and Python `call(..., reload_document=True)`.
- Document-operation lock, reuse/reload regression tests and live single-tab evidence. The existing duplicate app-launch guard remains enabled.
- Document-opening instructions for existing managed and ordinary GUI sessions.


## [0.4.0] - 2026-10-11

### Changed

- Refuse duplicate app launches by default across state directories and ordinary GUI instances. Intentional parallel sessions require `--allow-multiple` or Python `allow_multiple=True`.
- Serialize bridge starts through a per-user/app launch lock independent of session state. Existing healthy same-state sessions remain reusable; unknown instances are never adopted or stopped.

### Added

- Standard-library rocket example with CADCraft save/reopen/readback and closed nonconvex mesh STL output; the core convex exporter remains unchanged.
- Live workflow reports for all eight apps, original print/collage/vector/grading previews, motion/video examples and rocket visualization.
- Duplicate-launch regression tests and rocket topology/serialization tests.

### Documentation

- Clarified ArtCraft Bridge as a provider-independent local CLI/Python bridge for AI agents, including Codex usage, integration paths, verified workflows and AI integration FAQ.

## [0.3.0] - 2026-10-11

### Added

- Bridge-owned convex extrusion from live CADCraft closed profiles into STL and 3DFACE DXF via `cad-extrude`.
- `cad-export-stl` exports a validated convex closed triangular face boundary from CADCraft readback.
- Live 40 × 30 × 20 mm block test with CADCraft import/save/reopen and independent STL volume/topology checks.
- Reproducible example, STL preview and boundary documentation distinguishing mesh volume from native BRep solids.
- Geometry, serialization, invalid-input, translation-invariance and output-preservation tests.

## [0.2.0] - 2026-10-11

### Changed

- Renamed the project and repository from `recraft-bridge` to `artcraft-bridge` to identify the correct ArtCraft application suite.
- Renamed the Python package to `artcraft_bridge`, CLI to `artcraft-bridge`, environment variables to `ARTCRAFT_BRIDGE_*`, and default private state directory to `artcraft-bridge`. These are breaking changes; see the migration section in the README.
- Kept existing `v0.1.0` history and release unchanged.

### Added

- Reproducible CADCraft 0.5.0 3D wireframe cube example, native rendering and DXF save/reopen verification.
- Geometric checks for twelve 40 mm edges, eight XYZ vertices, connectivity and preservation of Z coordinates.
- README evidence and a CADCraft-generated preview. This verifies 3D polylines, not solid modeling or extrusion.

## [0.1.0] - 2026-10-11

### Added

- Local JSON control bridge for PhotoCraft, DesignCraft, VectorCraft, FilmCraft, LightCraft, EffectCraft, PdfCraft and CADCraft on macOS.
- Inventory, managed launch, state inspection, command discovery, raw method calls and managed shutdown.
- Configurable app, workspace and private state directories through CLI flags and environment variables.
- Authentication for PhotoCraft and PdfCraft, response ID matching, request/reply size limits and one wall-clock transport deadline.
- Process identity validation and a shared lifecycle lock for calls, starts and stops.
- Explicit opt-in for PdfCraft portable bundle copying/signing and for empty-session signal termination.
- Params-file input, installable CLI, semantic version policy and automated tests.
- MIT licensing for the bridge code and documentation.

### Verification

- The original local bridge was exercised against all eight installed apps. DesignCraft document creation, text insertion, save, readback and PNG render were verified.
- This repository's reproducible automated tests and current manual evidence are documented in [docs/verification.md](docs/verification.md).

### Limitations

- Experimental macOS support. Other platforms and all individual app commands have not been verified.
- No registered MCP server, hosted API, bundled ArtCraft apps or automatic graphical-session attachment.
