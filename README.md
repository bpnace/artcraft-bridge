# ArtCraft Bridge — local creative app automation for AI agents

**ArtCraft Bridge connects AI agents and local automation scripts to installed ArtCraft creative applications on macOS.** Its command-line interface and Python API let an agent discover app commands, inspect documents, execute supported operations and export files through local control interfaces. It is open-source, MIT-licensed and experimental.

Use it to give an AI coding agent a practical interface to CADCraft, DesignCraft, PhotoCraft, VectorCraft, FilmCraft, LightCraft, EffectCraft and PdfCraft. Verified examples cover all eight apps: print layout, layered photo collage, vector editing, color grading, short video/motion exports, PDF persistence and CAD meshes with bridge-assisted STL export.

Documentation updated 2026-10-11. Current bridge version **0.6.0**.

> Independent automation for ArtCraft Crafting Apps. This project is not affiliated with ArtCraft and does not use the Recraft cloud image service.

## Status and scope

Version `0.6.0` is experimental. It requires macOS, Python 3.9 or newer, and installed ArtCraft desktop apps. Its runtime uses only the Python standard library.

The bridge does not provide an MCP registration, a web API, a hosted service, or a PyPI package. Agents and scripts invoke its shell command directly. The installed apps perform their document operations. The optional CAD mesh extension computes convex extrusion and STL locally in the bridge; it makes no internet request.

Supported app identifiers are:

`photocraft`, `designcraft`, `vectorcraft`, `filmcraft`, `lightcraft`, `effectcraft`, `pdfcraft`, and `cadcraft`.

## What is ArtCraft Bridge for?

ArtCraft Bridge is a **local app automation bridge for AI agents**, built around a CLI and structured JSON results. An agent with authorized shell access can use the same commands as a human developer. Python-based agents can call the package directly. The bridge does not depend on a particular language model or AI provider.

Typical uses include:

- Letting a coding agent inspect and operate an installed creative application.
- Connecting a tool-calling AI agent to local desktop document workflows through a shell or Python tool.
- Reading app state and geometry to verify that an operation actually succeeded.
- Automating supported design, CAD and export operations with reproducible scripts.

The agent chooses the operations; the bridge handles local session control and app requests. Available features depend on the installed app version. A command catalog is discovery evidence, not proof that every creative operation works.

## How can Codex and other AI agents use ArtCraft apps?

An AI agent needs a way to execute local commands on the Mac where the ArtCraft apps are installed. Install ArtCraft Bridge there, give the agent the executable path and a dedicated workspace, and let it query the live command catalog before acting.

| Agent environment | Integration path | Evidence |
| --- | --- | --- |
| Codex with local shell access | Invoke `artcraft-bridge` or `python3 -m artcraft_bridge` as shell commands. | This project's live DesignCraft and CADCraft examples were executed from Codex on macOS. |
| Other local coding agents, including Claude Code or Gemini CLI | Invoke the same CLI when the host agent has authorized local shell access. | Intended CLI integration; these individual clients have not been integration-tested here. |
| Custom Python agents and AI tool frameworks | Import `artcraft_bridge.bridge` and expose selected functions as agent tools. | The Python API is used by the runnable CADCraft examples. Framework-specific adapters are not included. |
| Remote or chat-only assistants | Require a separate authorized execution tool on the local Mac. | ArtCraft Bridge itself provides no hosted connector or remote endpoint. |

### Agent quick start

After [installing from source](#install-from-source), an agent can start with these commands. Use the same workspace and state directory throughout the session:

```bash
artcraft-bridge --workspace "$PWD/agent-workspace" inventory
artcraft-bridge --workspace "$PWD/agent-workspace" start cadcraft
artcraft-bridge --workspace "$PWD/agent-workspace" commands cadcraft
artcraft-bridge --workspace "$PWD/agent-workspace" call cadcraft drawing.inspect \
  '{"entities": true, "limit": 100}'
```

Operational results are JSON on stdout. Errors are JSON on stderr with a nonzero exit code. An agent can inspect these results before choosing its next operation. Use the [command reference](#command-reference) and live app catalog for exact method names and parameters.

For a Python agent:

```python
from artcraft_bridge import bridge

bridge.configure(workspace="./agent-workspace")
available_apps = bridge.inventory()
bridge.start("cadcraft")
drawing = bridge.call("cadcraft", "drawing.inspect", {"entities": True, "limit": 100})
```

### Instructions you can give an AI agent

> Use ArtCraft Bridge to work with the installed ArtCraft apps on this Mac. Use a dedicated workspace, inspect the app inventory, start a managed session and read its live command catalog. Execute supported operations through the CLI or Python API. Verify results by inspecting the document and checking saved exports. Report which steps succeeded and which app capabilities are unavailable.

## Which AI-agent workflows have actually been tested?

**All eight apps completed representative live creative workflows on macOS on 2026-10-11.** Native save/reopen and exports were checked, rather than relying only on command catalogs. See [step-by-step operation examples and individual test records](docs/app-tests.md).

| App | Verified result | Evidence |
| --- | --- | --- |
| DesignCraft | A3 print poster, 19 editable objects, no text overflow, 3 mm bleed and embedded fonts | [Report](docs/evidence/designcraft.json) |
| PhotoCraft | Architecture collage, 18 editable layers, perspective transform and mask; identical reopened PNG | [Report](docs/evidence/photocraft.json) |
| VectorCraft | SVG import, native shape/color edit, 11 objects; PNG/SVG/PDF export | [Report](docs/evidence/vectorcraft.json) |
| LightCraft | Photo import and grading; PNG/JPEG exports and settings retained after restart | [Report](docs/evidence/lightcraft.json) |
| FilmCraft | Four-second 720p H.264 graphic clip with native dissolves; all 96 frames decoded | [Report](docs/evidence/filmcraft.json) · [Video](docs/media/filmcraft-after-hours.mp4) |
| EffectCraft | Four-second 720p keyframed animation; 96 distinct decoded frames | [Report](docs/evidence/effectcraft.json) · [Video](docs/media/effectcraft-after-hours.mp4) |
| CADCraft | Closed block and four-fin rocket meshes; DXF roundtrip and independently checked STL | [Block](docs/evidence/cadcraft.json) · [Rocket](docs/evidence/rocket.json) |
| PdfCraft | PDF open/rotate/save/reopen, retained text and restored orientation | [Report](docs/evidence/pdfcraft.json) |

### Print design and photo collage

| DesignCraft — native A3 poster | PhotoCraft — layered architecture collage |
| --- | --- |
| ![A3 poster created in DesignCraft with original geometric artwork](docs/images/app-tests/designcraft.png) | ![18-layer photo collage composed in PhotoCraft](docs/images/app-tests/photocraft.png) |

The print export requested PDF/X-4; trim, bleed, font embedding and output intent were checked, but formal PDF/X conformance validation was not run. The collage source photograph was generated with ImageGen; its composition, masks, transforms, shapes and text were edited in PhotoCraft.

### Vector, grading, video, motion and PDF examples

| VectorCraft — native vector edit | LightCraft — graded collage |
| --- | --- |
| ![VectorCraft orbit graphic](docs/images/app-tests/vectorcraft.png) | ![Collage with LightCraft exposure and color adjustments](docs/images/app-tests/lightcraft.jpg) |
| **FilmCraft — dissolves** | **EffectCraft — animated orbit** |
| ![Frame from the actual FilmCraft H.264 export](docs/images/app-tests/filmcraft.png) | ![EffectCraft composition preview](docs/images/app-tests/effectcraft.png) |
| **PdfCraft — saved PDF** | **CADCraft — closed-volume STL** |
| ![Native PdfCraft window showing the saved test poster](docs/images/app-tests/pdfcraft.png) | ![Independent preview of the CADCraft roundtripped closed block mesh](docs/images/cadcraft-solid-stl.png) |

The videos are short graphics workflows without audio. These tests do not verify every app feature, all import/export formats or arbitrary media editing. CADCraft 0.5.0 has no native BRep kernel, boolean solids, shaded 3D viewport or STL exporter; mesh construction/serialization is performed outside its kernel.

### Rocket model — CADCraft save/reopen and STL

![Independent 3D visualization of the rocket mesh read back from CADCraft](docs/images/app-tests/rocket.png)

**ORBIT / 01** is a 112 mm tall rocket with a 28 mm hull, a nose, a stylized closed nozzle and four integrated fins spanning 64 mm. Its 2,560 triangles form one connected watertight outward-oriented mesh. CADCraft saved and reopened all coordinates unchanged. Independent STL validation confirmed the closed boundary and approximately 53,389.16 mm³ volume.

The image is an independent visualization of the actual CADCraft readback mesh; CADCraft itself displays the faces in plan view. Preview colors are illustrative and are not stored in STL. This is a decorative closed mesh, not a native BRep object.

Reproduce it with the standard-library-only [rocket example](examples/cadcraft_rocket.py), using a fresh workspace and no other CADCraft instance:

```bash
python3 examples/cadcraft_rocket.py --workspace "$PWD/rocket-demo"
```

The example writes `outputs/rocket-source.dxf`, `outputs/rocket-cadcraft.dxf`, `outputs/rocket.stl` and `outputs/verification.json`. It exports STL from reopened CADCraft face data and leaves the saved drawing open. Import STL as millimetres because STL carries no unit field. The rocket is a separate nonconvex example; the bridge's general [convex exporter scope](#supported-scope) is unchanged. See [recorded rocket checks](docs/evidence/rocket.json) or [download the verified STL](docs/models/rocket.stl).

## AI integration FAQ

### Is ArtCraft Bridge an MCP server?

No. ArtCraft Bridge currently exposes a local CLI and Python API. Agents can invoke them through their existing shell or Python tools. An MCP wrapper could expose selected bridge operations, but no MCP server or automatic tool registration is included.

### Does it work with any AI model?

The bridge does not call an AI model. It is provider-independent: an agent can use it if its runtime supports authorized local shell execution or Python calls. Model-specific adapters and hosted chat integrations are not bundled.

### Does the bridge require a cloud API key?

The bridge's local control connection does not require an AI-provider API key. Your chosen AI agent and the installed ArtCraft apps have their own access requirements. Local app control does not imply that every app feature runs offline.

### Can AI agents create 3D objects and export STL with CADCraft?

The core exporter produces a closed convex triangle mesh from a straight closed CADCraft profile and exports STL. The separate rocket example builds a nonconvex radial mesh and roundtrips it through CADCraft before writing STL. It verifies the mesh after CADCraft saves and reopens the DXF. Native CADCraft solid modeling, booleans and a general-purpose CAD kernel are not provided; see [supported mesh scope](#supported-scope).

## Install from source

Clone the repository, or download and unpack its source ZIP.

```sh
git clone https://github.com/bpnace/artcraft-bridge.git
cd artcraft-bridge
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade "pip>=21.3" "setuptools>=61" wheel
.venv/bin/python -m pip install --no-build-isolation -e .
. .venv/bin/activate
```

If the editable install reports that `setuptools` is unavailable, install it in the virtual environment and rerun the install:

```sh
.venv/bin/python -m pip install setuptools
.venv/bin/python -m pip install --no-build-isolation -e .
```

After activating that environment, the installed console command is `artcraft-bridge`. The module entry point is equivalent:

```sh
artcraft-bridge --version
python3 -m artcraft_bridge --version
```

For a source checkout without installation, run the module with its source directory on `PYTHONPATH`:

```sh
PYTHONPATH=src python3 -m artcraft_bridge --version
```

## Configuration

Global options must precede the subcommand. Environment variables provide the same defaults.

| Option | Environment variable | Default | Purpose |
| --- | --- | --- | --- |
| `--apps-dir DIR` | `ARTCRAFT_BRIDGE_APPS_DIR` | `/Applications` | Directory containing the ArtCraft `.app` bundles. |
| `--workspace DIR` | `ARTCRAFT_BRIDGE_WORKSPACE` | Current directory | Directory where app-visible output is created. |
| `--state-dir DIR` | `ARTCRAFT_BRIDGE_STATE_DIR` | `~/Library/Application Support/artcraft-bridge` | Private bridge state, profiles, tokens, locks, and launch records. |

Command-line options override environment variables. A managed session is tied to its launch workspace and app directory; incompatible reuse is rejected. Use its original options to reuse or stop it. A separate `--state-dir` separates state but does not bypass the default duplicate-instance guard; intentional parallel launches also require `--allow-multiple`. Use a dedicated workspace for automation runs. The bridge creates `outputs/` inside that workspace for files it writes or exposes to apps.

Example with explicit, portable locations:

```sh
artcraft-bridge --apps-dir /Applications --workspace "$PWD" start designcraft
```

## Command reference

Operational commands write structured JSON to standard output. Errors are JSON on standard error with a nonzero exit status; help and version output are plain text. Use `--timeout SECONDS` with `call`; the value must be greater than zero and no more than `55`.

| Command | Result |
| --- | --- |
| `inventory` | Lists supported apps and reports whether their bundles are present under `--apps-dir`. |
| `start APP` | Reuses a healthy recorded session, or starts one when no other instance is running. Use `--allow-multiple` only for intentional parallel sessions. |
| `inspect APP` | Reads the current UI state from a managed session. |
| `commands APP` | Returns the app's current command catalog. Query this before invoking app-specific actions. |
| `open-document APP PATH [--reload]` | Reuse canonical file paths in CADCraft, PhotoCraft, PdfCraft and VectorCraft. Reload is limited to CADCraft/PhotoCraft. |
| `call APP METHOD [JSON]` | Sends an app method with an optional JSON object parameter. |
| `call APP METHOD --params-file FILE` | Reads the JSON object parameter from `FILE`. Use this for nontrivial parameters and file paths. |
| `stop APP` | Requests a safe stop for a session owned by this bridge. |
| `cad-extrude --height N --units mm --name NAME` | Extrudes a supported CADCraft profile in the bridge and writes STL plus triangular DXF; use `--handle HANDLE` for a drawing with multiple entities. |
| `cad-export-stl --units mm --name NAME` | Writes STL from the current CADCraft convex closed triangular face mesh. |

Typical read-only sequence:

```sh
artcraft-bridge start designcraft
artcraft-bridge inspect designcraft
artcraft-bridge commands designcraft
artcraft-bridge stop designcraft
```

For most apps, `inspect` calls `ui.inspect`, `commands` calls `engine.commands`, and application actions use `engine.execute`. PdfCraft uses JSON-RPC methods such as `ui.state`, `ui.commands`, `ui.command`, and `ui.open` instead. The catalog returned by `commands` is authoritative for the installed app version.

### Passing parameters safely

The positional `JSON` argument and `--params-file` must contain a JSON object. Put parameters in a file when a command writes to the workspace. This avoids shell escaping errors and makes the destination absolute before it reaches the app.

The following DesignCraft example creates an A4 document, adds a text frame, inspects it, and saves it under the current workspace's `outputs/` directory. These create, text, inspect, and save operations were exercised against the prototype. Run it only in a workspace where you want that document created.

```sh
bridge() { artcraft-bridge --workspace "$PWD" "$@"; }

bridge start designcraft

python3 - <<'PY'
import json
from pathlib import Path

outputs = Path.cwd().resolve() / "outputs"
outputs.mkdir(parents=True, exist_ok=True)

requests = {
    "design-new.json": {
        "command": "file.new",
        "params": {"preset": "A4", "title": "artcraft-bridge example"},
    },
    "design-text.json": {
        "command": "frame.create",
        "params": {
            "rect": [36, 36, 500, 100],
            "content": "text",
            "text": "artcraft-bridge controls a local ArtCraft session.",
        },
    },
    "design-save.json": {
        "path": str(outputs / "artcraft-bridge-example.designcraft"),
    },
    "design-render.json": {
        "path": str(outputs / "artcraft-bridge-example.png"),
        "page": 0,
        "scale": 1,
    },
}

for name, request in requests.items():
    (outputs / name).write_text(json.dumps(request) + "\n", encoding="utf-8")
PY

bridge call designcraft engine.execute --params-file outputs/design-new.json
bridge call designcraft engine.execute --params-file outputs/design-text.json
bridge call designcraft document.inspect '{}'
bridge call designcraft app.save --params-file outputs/design-save.json
bridge call designcraft ui.render --params-file outputs/design-render.json
bridge stop designcraft
```

The `app.save` and `ui.render` methods were also exercised against the prototype. `ui.render` writes the first page as a PNG preview. Selected checked previews and path-free test reports are included in this repository; private native projects and runtime state are excluded.

## PdfCraft requires an explicit portable copy

PdfCraft starts only when `--portable-copy` is supplied:

```sh
artcraft-bridge start pdfcraft --portable-copy
```

The bridge copies the user-installed PdfCraft bundle into its private state directory, adds its portable marker and data directory, runs `xattr -cr` on that copy, and ad-hoc signs that copy. It never clears attributes or signs the original bundle under `--apps-dir`.

Stopping PdfCraft also requires an explicit acknowledgement:

```sh
artcraft-bridge stop pdfcraft --allow-empty-pdf-termination
```

Before sending `SIGTERM`, the bridge reads PdfCraft state and refuses to continue unless `documents` is exactly `[]`; it also verifies that the process is the bridge-owned process. This is a safety check, not a transaction: a person can open or change a document after the check and before termination. Do not interact with the PdfCraft window during that short interval.

## Why did multiple app instances open?

Before 0.4.0, launch discovery and locking were limited to the chosen `--state-dir`. Each separate test directory could therefore launch another process of the same app. Direct executable launches did not reuse ordinary app windows. PdfCraft additionally copied its bundle into a fresh portable profile, so repeated sessions could leave several app bundles visible to macOS even after their processes stopped.

Version **0.4.0** checks running ArtCraft executable paths before starting and serializes bridge launches through one private per-user/app lock independent of the selected state directory. A healthy session in the same state directory is reused. Otherwise, an already-running instance blocks a new launch, without being adopted or terminated. Reuse its original workspace/state options, or close it normally before starting a different session.

For intentional parallel tests only:

```bash
artcraft-bridge --workspace "$PWD/isolated-demo" --state-dir "$PWD/isolated-state" \
  start cadcraft --allow-multiple
```

Python callers use `bridge.start("cadcraft", allow_multiple=True)`. The guard observes executable paths via `ps`; it cannot prevent a person or another tool from starting an app outside the bridge at the same moment. Unknown or unsaved windows are never closed automatically. [Live guard verification](docs/evidence/session-guard.json) confirms same-state reuse and cross-state refusal without an additional process. The lock lives under `~/Library/Application Support/artcraft-bridge/launch-locks`, even when custom session state is used.

`stop` retains app profiles and PdfCraft portable copies so documents and preferences are not discarded. The documented live tests explicitly removed their disposable PdfCraft copies after confirming the owned process was stopped, while preserving data separately. Do not delete or terminate a running copy to tidy the app list.

## Cross-app document reuse in 0.6.0

The follow-up live test created one new document/project or imported one image in each remaining app. The five closed apps were started once first; subsequent operations reused that session. VectorCraft retained its already-running desktop process. Final checks found exactly one process and one main window per app.

| App | Repeated operation | Verified result |
|---|---|---|
| PhotoCraft | Three guarded `app.open` calls | One `.pcraft` tab; the new guard activates the original. Native/raw reopening had created a second tab before the fix. |
| PdfCraft | Three guarded `ui.open` calls | One PDF tab with the same document ID; inactive-tab activation was also verified. Native/raw reopening had created a second tab before the fix. |
| LightCraft | Three repeated copy imports | One library photo and one source-file copy; native content deduplication recognizes all repeats. |
| FilmCraft | Three `file.open` calls | One saved project and one sequence, same process/window. This reloads the single project. |
| EffectCraft | Three `file.open` calls | One saved project and one composition, same process/window. This reloads the single project. |
| VectorCraft | New document and repeated existing-tab activation | One new native document beside the existing drawing; two tabs remain. The ordinary GUI process was preserved. Managed path reuse is regression-tested; no live managed-session claim is made for this window. |

Each managed session also survived three repeated `start` calls without relaunch. Three attempts to start another VectorCraft session were refused while its ordinary desktop instance was open. See [sanitized evidence](docs/evidence/cross-app-reuse.json).

**Version 0.6.0 includes the PhotoCraft, PdfCraft and VectorCraft opening guards.** `open-document photocraft PATH` uses `app.open`; `open-document pdfcraft PATH` uses `ui.open`. Raw opening calls require absolute paths. PhotoCraft supports explicit reload only when all matching tabs are saved; PdfCraft reload is refused. PdfCraft can activate an inactive tab only when its name and UI button are unambiguous, and checks its document ID and path afterward. Unclear state causes an error without another open.

For the existing unmanaged VectorCraft window, select the existing document tab for further edits. There is no supported way to enable its control listener after startup. The bridge refuses to start another instance or send an unguarded file handoff. Three guarded open attempts on that window were refused without creating documents; its two tabs and process remained unchanged. Create a new document exactly once per new design. A native menu or macOS file handoff bypasses the bridge guards. FilmCraft/EffectCraft tests cover saved projects; they do not establish protection against reloading unsaved edits. `file.new` is intentionally a creation operation: repeating it can create several new documents. The bridge does not identify repeated intent across arbitrary agent calls.

PdfCraft's private test bundle under Documents could not be signed because Finder metadata was present. A private runtime under `/private/tmp` allowed the test; that temporary state must be retained to control this still-running test session and may not survive reboot. No original installed bundle was modified.

### VectorCraft guard and examples

```sh
artcraft-bridge --workspace "$SESSION_WORKSPACE" --state-dir "$SESSION_STATE_DIR" open-document vectorcraft /absolute/path/to/design.svg
artcraft-bridge --workspace "$SESSION_WORKSPACE" --state-dir "$SESSION_STATE_DIR" call vectorcraft app.open '{"path":"/absolute/path/to/design.svg"}'
```

VectorCraft 0.9.0 exposes tab titles through `ui.inspect`, and the active document path through `document.inspect`. The bridge serializes opening, temporarily activates tabs to inspect their paths, then selects the matching tab. Unsaved edits are preserved. Relative stored paths are resolved against the managed app workspace; requested opening paths must be absolute. Inspection failure prevents another open. A pathless imported or untitled tab prevents proving that a new path is absent, so the bridge refuses that open; save pathless documents before opening a new file, or select the existing tab directly to continue editing it. New-document creation remains a separate, single intentional action.

This behavior follows the [installed protocol implementation](https://github.com/storytold/vectorcraft/blob/10f1c56a861869936af0027cef14b1cf5d8cf515/crates/ui-egui/src/control.rs) and [document inspection schema](https://github.com/storytold/vectorcraft/blob/10f1c56a861869936af0027cef14b1cf5d8cf515/crates/engine/src/inspect.rs). Native menus, Finder/macOS file handoffs and other opening commands bypass bridge interception. This fixes the bridge's supported opening routes; it does not patch the installed app's native open handler.

## Open new documents in an already-running app

**Create or open another document in the existing app process.** A new design is a document operation, not a reason to launch another app. Keep existing documents open when the app supports tabs; save work before operations that replace the active drawing.

### Existing bridge-managed session

Reuse the session's original `--workspace` and `--state-dir` options. Query its live command catalog, then invoke the supported document-create or document-open method. Do not call `stop`, change state directories, or enable `--allow-multiple` to make another design.

Since **0.5.0**, CADCraft `app.open` reuses an already-open canonical file path. The convenience command is:

```bash
artcraft-bridge --workspace "$SESSION_WORKSPACE" --state-dir "$SESSION_STATE_DIR" open-document cadcraft /absolute/path/to/model.dxf
```

Raw method form:

```bash
artcraft-bridge --workspace "$SESSION_WORKSPACE" --state-dir "$SESSION_STATE_DIR"   call cadcraft app.open --params-file open-document.json
```

`open-document.json` contains an absolute path to a saved drawing:

```json
{"path": "/absolute/path/to/car-cadcraft.dxf"}
```

An existing dirty tab is activated with its edits preserved. To deliberately reload from disk, use `open-document cadcraft PATH --reload`, raw `call cadcraft app.open --params-file FILE --reload-document`, or Python `call("cadcraft", "app.open", {"path": absolute_path}, reload_document=True)`. Reload requires an existing source file and saved matching tabs. It closes those tabs in descending index order, then opens the file once. Raw `app.open` paths must be absolute. The same canonical-path reuse applies to managed PhotoCraft (`app.open`), PdfCraft (`ui.open`) and VectorCraft (`app.open` and path-based `engine.execute document.open`). VectorCraft and PdfCraft refuse `--reload`.

Discovery, switching, closing and opening share a document-operation lock, including explicit-state Python calls, and one request deadline after acquiring the lock. No failed mutation is automatically retried. Reload is not transactional: a load failure after saved tabs close leaves their files on disk. Inspect before retrying. Manual GUI actions do not participate in the bridge lock.

The live test found six saved copies of the seat file, removed five, and confirmed repeated opens and explicit reload retained one tab and the same app process. See [live document guard evidence](docs/evidence/document-guard.json).

The car test reused the existing CADCraft process, saved and reopened the new drawing, and preserved the saved rocket on disk. This verifies process reuse; it does not claim CADCraft keeps every drawing in a separate tab. Creation methods differ between apps: use the live catalog instead of guessing a universal `document.new` command.

### App opened normally from the desktop

The CLI cannot attach its control protocol to an ordinary GUI process that has no control listener. Use that app's native **File → New Document** or **File → Open** action through desktop automation. The bridge's launch guard blocks an additional process; it does not turn the existing GUI into a managed session.

For a genuinely new VectorCraft file, this macOS handoff was tested with an already-running ordinary GUI instance. It bypasses bridge guards and must not be repeated for a file whose tab is already open:

```bash
open -a /Applications/VectorCraft.app /absolute/path/to/new-design.svg
```

Both SVGs appeared as editable document tabs in the same process. For DesignCraft, use the native **File → Open…** dialog for `.designcraft` files: the tested installed bundle rejected Finder/LaunchServices opening of that extension even though its own Open dialog loaded the native files successfully. In the dialog, **Command–Shift–G** accepts an absolute path; confirm navigation, then press Open. Wait for each dialog to appear and keep the intended app foreground before sending keys.

### Verified desktop workflow, 2026-10-11

| App | Result in existing process | Verification |
| --- | --- | --- |
| DesignCraft | SIGNAL and GRID LAB native A3 documents in two tabs | Both complete layouts rendered with shapes/text and “No Errors” status. |
| VectorCraft | ORBIT CLUB and CITY DRIVE SVG documents in two tabs | Both complete compositions rendered as editable vectors. |
| CADCraft | Basic car drawing opened, saved and reopened | 11,800 faces; one watertight connected mesh; 120 × 56 × 46 mm; STL checked independently. |

Process IDs stayed unchanged throughout the test, and a final executable-path inventory found exactly one process per app. Desktop opening is an operator workflow; `open-document` targets managed CADCraft, PhotoCraft, PdfCraft and VectorCraft. It does not attach to unmanaged GUI apps.

### Why CADCraft shows a flat view of a 3D file

In the tested installed CADCraft 0.5.0, the viewport draws face edges in the XY plane. Z coordinates are stored and survive save/reopen, but the view does not provide a working shaded 3D camera/orbit renderer. Looking down the Z axis makes the car look flat and overlaps edges at different heights.

The car contains actual XYZ triangle coordinates, including a 46 mm height. Its STL is a closed 3D surface. The preview image was rendered independently from CADCraft's readback geometry; it is not a screenshot of CADCraft's viewport. The bridge generates the mesh and writes STL; CADCraft stores the imported `3DFACE` entities. This is a mesh workflow, not native parametric solid modelling.

The upstream [known gaps](https://github.com/storytold/cadcraft/blob/main/docs/gaps.md) list missing 3D views, orbit, visual styles and rendering. A full interactive 3D view requires a separate mesh viewer or a future CADCraft implementation; zooming the current XY viewport does not add that capability.

## Safety and behavior

- `start` only controls sessions that it created and recorded. It does not adopt ordinary app windows.
- A response timeout or closed control connection can leave an edit's result unknown. Inspect state before retrying; the bridge does not automatically retry a mutation.
- Some UI methods require an unobscured foreground app. If a call waits for a visible window, bring the app forward, for example `open -a DesignCraft`, then inspect state before attempting another mutation.
- For apps other than PdfCraft, `stop` requests the app's quit method. A save prompt remains open and the bridge does not force-kill the app.
- Local control channels are intended for the same machine. Some app protocols do not authenticate every connection. Keep state files private and do not expose local control ports.
- PhotoCraft and VectorCraft receive automation roots limited to the configured workspace and its `outputs/` directory. Those roots do not create a security sandbox, and the other apps do not receive that enforcement.

## CADCraft 3D cube — verified live

![A 40 mm XYZ wireframe cube rendered by CADCraft](docs/images/cadcraft-cube.png)

The image above is CADCraft's own `ui.render` output. The bridge created a real **3D wireframe cube** in CADCraft 0.5.0, saved it as DXF, reopened that DXF in CADCraft, and verified its geometry again.

- **12** entities of type `3D Polyline`, with **8** distinct XYZ vertices.
- Every edge is **40 mm** long; every vertex joins three edges.
- All expected coordinates survive saving and reopening, including **8 distinct Z levels**.
- The drawing uses metric units (`$INSUNITS = 4`).
- The native preview is **1400 × 1000** pixels.

This is a wireframe object, not a solid, a watertight surface mesh or a 3D-printable STL. The tested 0.5.0 command catalog exposes `3dpoly`, but no box, extrusion or solid-modeling command. CADCraft renders the drawing in its XY view; the cube's XYZ coordinates are rotated so this projection shows the shape. The projection is not evidence of a full 3D camera or solid renderer.

Run the same verified example from an installed source checkout, with a **fresh dedicated workspace**:

```sh
python3 examples/cadcraft_cube.py --workspace "$PWD/cadcraft-demo"
```

The example writes `outputs/artcraft-cube-40.dxf`, `outputs/artcraft-cube-40.png` and `outputs/cadcraft-cube-verification.json` under that workspace. It verifies geometry before saving and after reopening, refuses to overwrite existing example files or edit a reused managed session, and leaves the saved drawing visible. To close that managed test session:

```sh
artcraft-bridge --workspace "$PWD/cadcraft-demo" stop cadcraft
```

Use the same `--state-dir` for the example and subsequent CLI calls if you chose a custom one. See the [example source](examples/cadcraft_cube.py) and the [recorded verification result](docs/cadcraft-cube-verification.json). The report contains no local absolute paths or control tokens.

## Closed volume and STL — bridge extension

![STL surface preview, plotted independently from the exported file](docs/images/cadcraft-solid-stl.png)

**Verified in CADCraft 0.5.0 on 2026-10-11.** A 40 × 30 mm closed polyline was drawn in CADCraft. The bridge extruded its live coordinates by 20 mm into a closed convex triangle boundary, imported those twelve `3DFACE` triangles into CADCraft, saved and reopened the DXF, then wrote STL from CADCraft's inspected face coordinates. The exported block encloses **24,000 mm³**, with eight vertices and dimensions **40 × 30 × 20 mm**.

Independent validation with trimesh 4.12.2 reports `is_watertight`, `is_winding_consistent` and `is_volume` all true, Euler characteristic 2 and the expected dimensions and volume. The image above is an independent plot of the exported STL, not CADCraft's viewport. See the [recorded result](docs/cadcraft-solid-verification.json).

### What runs where

CADCraft owns the source profile and the imported DXF triangle faces. **ArtCraft Bridge performs extrusion and STL serialization.** The app has no native `box`, `extrude` or `exportstl` command in the tested 341-command catalog. This produces a genuine closed mesh boundary enclosing a volume, not a CADCraft BRep/ACIS solid. CADCraft displays face edges in XY projection; it does not provide a shaded 3D solid viewport. [Upstream format limitations](https://github.com/storytold/cadcraft/blob/main/docs/file-format-parity.md) and [roadmap](https://github.com/storytold/cadcraft/blob/main/ROADMAP.md) describe the missing native 3D/STL work.

### Reproduce the complete live test

From an installed source checkout, use a fresh dedicated workspace and a new managed session:

```bash
python3 examples/cadcraft_solid.py --workspace "$PWD/cadcraft-solid-demo"
```

The example saves the original profile, exports a bridge STL and 3DFACE DXF, imports the latter into CADCraft, saves/reopens it and exports `outputs/block-cadcraft-reopened.stl` from the reopened faces. It leaves the saved mesh drawing open. It refuses nonempty output directories and reused managed sessions. Use `--state-dir DIR` consistently for session state. Close other CADCraft instances first; parallel sessions require explicit `--allow-multiple`.

### Use your own profile

Create a closed straight lightweight polyline in the managed CADCraft drawing, then run:

```bash
artcraft-bridge --workspace "$PWD/my-cad-project" cad-extrude \
  --height 20 --units mm --name my-part
```

This writes `outputs/my-part.stl` and `outputs/my-part.dxf`, without replacing the open drawing. If the drawing contains several entities, select the source with `--handle HANDLE` from `drawing.inspect`. Coordinates must explicitly be interpreted as millimetres; STL itself carries no unit field. Existing output files are never overwritten.

To import the generated face mesh into CADCraft, use `app.open` with its absolute DXF path. You can then save/reopen it through the normal bridge calls. To export the current CADCraft face mesh:

```bash
artcraft-bridge --workspace "$PWD/my-cad-project" cad-export-stl \
  --units mm --name my-part-from-cadcraft
```

### Supported scope

The dependency-free exporter accepts simple strictly convex closed profiles made of straight segments and a positive extrusion height. Mesh export accepts convex closed consistently oriented triangular `3DFACE` boundaries. Holes, concave outlines, curved/bulged segments, wide polylines, quads, booleans, bevels and native solid entities are rejected. It checks nondegenerate triangles, paired opposite edge directions, convex boundary planes and positive volume. This is a bounded extrusion/export tool, not a general CAD kernel. The live sample passes independent topology/volume checks; no physical print was performed.

## Migration from 0.1.0

Version 0.1.0 used the mistaken name `recraft-bridge`. Version 0.2.0 uses **ArtCraft Bridge** throughout:

| 0.1.0 | 0.2.0 |
| --- | --- |
| `recraft-bridge` CLI / distribution | `artcraft-bridge` |
| `recraft_bridge` Python module | `artcraft_bridge` |
| `RECRAFT_BRIDGE_*` variables | `ARTCRAFT_BRIDGE_*` |
| `~/Library/Application Support/recraft-bridge` | `~/Library/Application Support/artcraft-bridge` |

Close old bridge-managed sessions with the old CLI and their original workspace before upgrading. Uninstall the old distribution, install the new one, and update scripts, environment variables and repository remotes. Old state is not migrated or deleted automatically. The existing `v0.1.0` tag and release remain historical artifacts under their original package name.

## Observed prototype evidence

The prototype successfully started or reused, queried, and stopped these locally installed versions. The catalog count shows that the catalog was returned; it does not prove every listed action works.

| App | Observed version | Catalog entries |
| --- | ---: | ---: |
| PhotoCraft | 0.7.0 | 858 |
| DesignCraft | 0.6.0 | 555 |
| VectorCraft | 0.9.0 | 992 |
| FilmCraft | 0.6.0 | 693 |
| LightCraft | 0.6.0 | 453 |
| EffectCraft | 0.8.0 | 669 |
| PdfCraft | 0.6.0 | 185 |
| CADCraft | 0.5.0 | 341 |

Installed app versions and catalogs can differ. Run `commands APP` against the target Mac before relying on an action.

## Test

Run the package test suite from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

See [the architecture document](docs/architecture.md) for the session, transport, and safety model.

## License

The bridge code and documentation are licensed under the [MIT License](LICENSE). ArtCraft applications and any imported or exported media retain their own licensing terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Further documentation

- [Architecture and protocol boundaries](docs/architecture.md)
- [Verification evidence](docs/verification.md)
- [Versioning and release procedure](VERSIONING.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [External applications and protocol references](THIRD_PARTY_NOTICES.md)
