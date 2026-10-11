# Verification evidence for 0.1.0

The reusable package was tested on macOS with Python 3.9 on 2026-10-11. This is a compatibility observation from one Mac, not a guarantee for every ArtCraft build or every command.

## Automated checks

- 27 standard-library unit tests passed using both the source module and the installed package.
- Version, help and inventory CLI entry points were exercised.
- `VERSION`, the package version and the changelog heading agree at `0.1.0`.
- An editable installation and wheel/source-distribution builds were exercised in a dedicated virtual environment. Build tools are install-time dependencies; the bridge has no third-party runtime dependency.

Tests cover framing, response ID matching, malformed/rejected/oversized replies, authentication order for both authenticated protocols, total transport deadlines, no automatic mutation replay, private state permissions, stale process rejection, configured app discovery, workspace mismatch rejection, shared lifecycle locking, explicit PdfCraft lifecycle guards and params-file CLI input.

## Live application checks

The package was run with a dedicated workspace and state directory against all eight applications. Each app was launched, its state and command catalog were read, and the bridge-owned test session was closed.

| App | Version | Catalog entries | State/catalog | Cleanup |
| --- | --- | ---: | --- | --- |
| PhotoCraft | 0.7.0 | 858 | Passed | Closed |
| DesignCraft | 0.6.0 | 555 | Passed | Closed |
| VectorCraft | 0.9.0 | 992 | Passed | Closed |
| FilmCraft | 0.6.0 | 693 | Passed | Closed |
| LightCraft | 0.6.0 | 453 | Passed | Closed |
| EffectCraft | 0.8.0 | 669 | Passed | Closed |
| PdfCraft | 0.6.0 | 185 | Passed | Closed |
| CADCraft | 0.5.0 | 341 | Passed | Closed |

The README's DesignCraft shell example was executed with the installed console command. It created an A4 document, inserted the documented text, read it back, saved a native `.designcraft` document, rendered a 595 × 842 PNG and closed the saved session. Test documents, exports, raw state, tokens, logs and local absolute paths are deliberately excluded from this repository.

PdfCraft used the explicitly opted-in private portable copy and empty-session termination path. Its installed application was not modified. Other apps used their regular quit method.

## Not verified

- Every individual catalog action, complex design work, video editing or 3D modeling.
- All import/export formats, large media, long renders or recovery from app crashes.
- Other app versions, macOS versions, CPU architectures or operating systems.
- GitHub-hosted CI before the workflow has actually run.
- Package-registry publication, an MCP integration, or an official upstream endorsement.

Repeat affected live checks before changing an integration's compatibility claims. Use a disposable workspace and separate runtime state. Do not commit the resulting app profiles or project files.
