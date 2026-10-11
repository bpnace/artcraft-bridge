# recraft-bridge

`recraft-bridge` is an experimental local command-line bridge for the ArtCraft Crafting Apps on macOS. It starts and controls isolated, bridge-managed desktop sessions through the apps' local control interfaces.

> **Name clarification:** this project is independent software for ArtCraft Crafting Apps. It is not the Recraft cloud AI image service, has no official affiliation with ArtCraft or Recraft, and does not call Recraft services.

## Status and scope

Version `0.1.0` is experimental. It requires macOS, Python 3.9 or newer, and installed ArtCraft desktop apps. Its runtime uses only the Python standard library.

The bridge does not provide an MCP registration, a web API, a hosted service, or a PyPI package. Agents and scripts invoke its shell command directly. The installed apps perform their own work; the bridge makes no network request on their behalf.

Supported app identifiers are:

`photocraft`, `designcraft`, `vectorcraft`, `filmcraft`, `lightcraft`, `effectcraft`, `pdfcraft`, and `cadcraft`.

## Install from source

Clone the repository, or download and unpack its source ZIP.

```sh
git clone https://github.com/bpnace/recraft-bridge.git
cd recraft-bridge
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

After activating that environment, the installed console command is `recraft-bridge`. The module entry point is equivalent:

```sh
recraft-bridge --version
python3 -m recraft_bridge --version
```

For a source checkout without installation, run the module with its source directory on `PYTHONPATH`:

```sh
PYTHONPATH=src python3 -m recraft_bridge --version
```

## Configuration

Global options must precede the subcommand. Environment variables provide the same defaults.

| Option | Environment variable | Default | Purpose |
| --- | --- | --- | --- |
| `--apps-dir DIR` | `RECRAFT_BRIDGE_APPS_DIR` | `/Applications` | Directory containing the ArtCraft `.app` bundles. |
| `--workspace DIR` | `RECRAFT_BRIDGE_WORKSPACE` | Current directory | Directory where app-visible output is created. |
| `--state-dir DIR` | `RECRAFT_BRIDGE_STATE_DIR` | `~/Library/Application Support/recraft-bridge` | Private bridge state, profiles, tokens, locks, and launch records. |

Command-line options override environment variables. A managed session is tied to its launch workspace and app directory; incompatible reuse is rejected. Use the original options to stop it, or a separate `--state-dir` for independent configurations. Use a dedicated workspace for automation runs. The bridge creates `outputs/` inside that workspace for files it writes or exposes to apps.

Example with explicit, portable locations:

```sh
recraft-bridge --apps-dir /Applications --workspace "$PWD" start designcraft
```

## Command reference

Operational commands write structured JSON to standard output. Errors are JSON on standard error with a nonzero exit status; help and version output are plain text. Use `--timeout SECONDS` with `call`; the value must be greater than zero and no more than `55`.

| Command | Result |
| --- | --- |
| `inventory` | Lists supported apps and reports whether their bundles are present under `--apps-dir`. |
| `start APP` | Starts an isolated managed app session, or reuses a healthy session that this bridge previously started. |
| `inspect APP` | Reads the current UI state from a managed session. |
| `commands APP` | Returns the app's current command catalog. Query this before invoking app-specific actions. |
| `call APP METHOD [JSON]` | Sends an app method with an optional JSON object parameter. |
| `call APP METHOD --params-file FILE` | Reads the JSON object parameter from `FILE`. Use this for nontrivial parameters and file paths. |
| `stop APP` | Requests a safe stop for a session owned by this bridge. |

Typical read-only sequence:

```sh
recraft-bridge start designcraft
recraft-bridge inspect designcraft
recraft-bridge commands designcraft
recraft-bridge stop designcraft
```

For most apps, `inspect` calls `ui.inspect`, `commands` calls `engine.commands`, and application actions use `engine.execute`. PdfCraft uses JSON-RPC methods such as `ui.state`, `ui.commands`, `ui.command`, and `ui.open` instead. The catalog returned by `commands` is authoritative for the installed app version.

### Passing parameters safely

The positional `JSON` argument and `--params-file` must contain a JSON object. Put parameters in a file when a command writes to the workspace. This avoids shell escaping errors and makes the destination absolute before it reaches the app.

The following DesignCraft example creates an A4 document, adds a text frame, inspects it, and saves it under the current workspace's `outputs/` directory. These create, text, inspect, and save operations were exercised against the prototype. Run it only in a workspace where you want that document created.

```sh
bridge() { recraft-bridge --workspace "$PWD" "$@"; }

bridge start designcraft

python3 - <<'PY'
import json
from pathlib import Path

outputs = Path.cwd().resolve() / "outputs"
outputs.mkdir(parents=True, exist_ok=True)

requests = {
    "design-new.json": {
        "command": "file.new",
        "params": {"preset": "A4", "title": "recraft-bridge example"},
    },
    "design-text.json": {
        "command": "frame.create",
        "params": {
            "rect": [36, 36, 500, 100],
            "content": "text",
            "text": "recraft-bridge controls a local ArtCraft session.",
        },
    },
    "design-save.json": {
        "path": str(outputs / "recraft-bridge-example.designcraft"),
    },
    "design-render.json": {
        "path": str(outputs / "recraft-bridge-example.png"),
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

The `app.save` and `ui.render` methods were also exercised against the prototype. `ui.render` writes the first page as a PNG preview. No edited document or generated image is bundled in this repository.

## PdfCraft requires an explicit portable copy

PdfCraft starts only when `--portable-copy` is supplied:

```sh
recraft-bridge start pdfcraft --portable-copy
```

The bridge copies the user-installed PdfCraft bundle into its private state directory, adds its portable marker and data directory, runs `xattr -cr` on that copy, and ad-hoc signs that copy. It never clears attributes or signs the original bundle under `--apps-dir`.

Stopping PdfCraft also requires an explicit acknowledgement:

```sh
recraft-bridge stop pdfcraft --allow-empty-pdf-termination
```

Before sending `SIGTERM`, the bridge reads PdfCraft state and refuses to continue unless `documents` is exactly `[]`; it also verifies that the process is the bridge-owned process. This is a safety check, not a transaction: a person can open or change a document after the check and before termination. Do not interact with the PdfCraft window during that short interval.

## Safety and behavior

- `start` only controls sessions that it created and recorded. It does not adopt ordinary app windows.
- A response timeout or closed control connection can leave an edit's result unknown. Inspect state before retrying; the bridge does not automatically retry a mutation.
- Some UI methods require an unobscured foreground app. If a call waits for a visible window, bring the app forward, for example `open -a DesignCraft`, then inspect state before attempting another mutation.
- For apps other than PdfCraft, `stop` requests the app's quit method. A save prompt remains open and the bridge does not force-kill the app.
- Local control channels are intended for the same machine. Some app protocols do not authenticate every connection. Keep state files private and do not expose local control ports.
- PhotoCraft and VectorCraft receive automation roots limited to the configured workspace and its `outputs/` directory. Those roots do not create a security sandbox, and the other apps do not receive that enforcement.

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
