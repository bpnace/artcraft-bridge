# Verification evidence for 0.3.0

## CADCraft closed-volume and STL live test

CADCraft 0.5.0 created a 40 × 30 mm closed polyline. ArtCraft Bridge extruded it by 20 mm, imported the generated 12 triangular 3DFACE entities into CADCraft, saved and reopened that DXF, and verified identical XYZ triangles. The bridge wrote STL directly from the reopened face readback. This is a closed convex triangle mesh enclosing 24,000 mm³, not a native BRep solid.

An independent trimesh 4.12.2 load verifies watertight topology, consistent orientation, is_volume, Euler characteristic 2, dimensions 40 × 30 × 20 mm and volume 24,000 mm³. The path-free report is [cadcraft-solid-verification.json](cadcraft-solid-verification.json). The preview is plotted from the exported STL with matplotlib, not the CADCraft viewport. The exporter needs no runtime dependencies. All 45 unit tests pass locally.

Live probes of box, extrude and exportstl returned unknown command; the 341-command catalog contains none. Upstream source snapshot 77de6af455acf4802bfaf77970f1236002e649f5 supports Face3d import/save/readback but has no native solid kernel/STL writer. See [format parity](https://github.com/storytold/cadcraft/blob/77de6af455acf4802bfaf77970f1236002e649f5/docs/file-format-parity.md).

## Historical CADCraft 0.2.0 live 3D geometry test

On 2026-10-11 the renamed package created a 40 mm cube in CADCraft 0.5.0 using twelve `3dpoly` commands. It read `drawing.inspect`, saved via `app.save`, reopened the DXF via `app.open`, repeated the geometry checks and rendered a native PNG via `ui.render`.

The checks verify twelve 3D polyline entities, eight distinct XYZ vertices, the exact intended rotated cube edges, edge lengths within 2 × 10⁻⁶ mm of 40 mm and degree three at every vertex. Eight distinct Z levels survive reopening. The DXF header records millimetres (`$INSUNITS = 4`).

The runnable example is [examples/cadcraft_cube.py](../examples/cadcraft_cube.py). Its path-free result is [cadcraft-cube-verification.json](cadcraft-cube-verification.json), and its native preview is [images/cadcraft-cube.png](images/cadcraft-cube.png). Six automated example checks cover valid geometry, flattened Z, wrong entity types, missing edges, duplicate edges and refusal to edit a reused session. All 33 repository tests pass.

This proves creation and persistence of 3D wireframe geometry. It does not prove solid modeling, extrusion, a watertight mesh, STL output or a general 3D camera. The target command catalog does not expose box/extrusion/solid commands. CADCraft's render is an XY projection of the rotated spatial geometry.

## Renaming checks

The package, Python module, CLI, environment-variable prefix, repository links and default state directory now use `artcraft-bridge` / `artcraft_bridge` / `ARTCRAFT_BRIDGE_*`. The version is `0.2.0`. Tests, installed CLI and package builds are checked after the rename. Historical v0.1.0 artifacts are retained.

## Historical verification for 0.1.0

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
