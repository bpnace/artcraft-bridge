#!/usr/bin/env python3
"""Local ArtCraft desktop control client. Python standard library only."""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import plistlib
import secrets
import shutil
import signal
import platform
import socket
import subprocess
import sys
import time
import uuid

from . import __version__

BASE = Path(os.environ.get("ARTCRAFT_BRIDGE_WORKSPACE", str(Path.cwd()))).expanduser().resolve()
RUNTIME = Path(os.environ.get("ARTCRAFT_BRIDGE_STATE_DIR", str(Path.home() / "Library" / "Application Support" / "artcraft-bridge"))).expanduser().resolve()
LAUNCH_LOCK_DIR = Path.home() / "Library" / "Application Support" / "artcraft-bridge" / "launch-locks"
APPS_DIR = Path(os.environ.get("ARTCRAFT_BRIDGE_APPS_DIR", "/Applications")).expanduser().resolve()


def configure(workspace=None, state_dir=None, apps_dir=None):
    """Configure paths before using the Python API. Call once per process."""
    global BASE, RUNTIME, APPS_DIR
    if workspace is not None:
        BASE = Path(workspace).expanduser().resolve()
    if state_dir is not None:
        RUNTIME = Path(state_dir).expanduser().resolve()
    if apps_dir is not None:
        APPS_DIR = Path(apps_dir).expanduser().resolve()
APPS = {
    "photocraft": {"name": "PhotoCraft", "auth": True, "roots": True},
    "designcraft": {"name": "DesignCraft"},
    "vectorcraft": {"name": "VectorCraft", "roots": True},
    "filmcraft": {"name": "FilmCraft"},
    "lightcraft": {"name": "LightCraft"},
    "effectcraft": {"name": "EffectCraft"},
    "pdfcraft": {"name": "PdfCraft", "rpc": True},
    "cadcraft": {"name": "CADCraft"},
}
MAX_REQUEST = 1024 * 1024
MAX_REPLY = 8 * 1024 * 1024


class BridgeError(Exception):
    pass


class SessionConflict(BridgeError):
    """An existing session belongs to different launch configuration."""


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(".tmp")
    fd = os.open(str(temp), os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    os.replace(str(temp), str(path))


def state_path(app):
    return RUNTIME / app / "state.json"


def load_state(app):
    try:
        state = json.loads(state_path(app).read_text())
    except FileNotFoundError:
        raise BridgeError("App has no managed control session; run start first")
    if state.get("app") != app or not isinstance(state.get("port"), int):
        raise BridgeError("Invalid managed session")
    if state.get("workspace") != str(BASE) or state.get("apps_dir") != str(APPS_DIR):
        raise SessionConflict("Session configuration differs; use its original --workspace and --apps-dir to stop it, or choose a separate --state-dir")
    if not process_matches(app, state.get("pid"), state.get("executable"), state.get("process_identity")):
        raise BridgeError("Managed app is no longer running; run start again")
    return state


def process_identity(pid):
    result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "comm="],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def process_matches(app, pid, binary=None, identity=None):
    if not isinstance(pid, int) or pid <= 0:
        return False
    current = process_identity(pid)
    return bool(current and current.endswith(" " + (binary or executable(app)))
                and identity is not None and current == identity)


def executable(app):
    name = APPS[app]["name"]
    return str(APPS_DIR / (name + ".app") / "Contents" / "MacOS" / name)


def running_instances(app):
    """Find app executables across profiles without reading command arguments."""
    result = subprocess.run(["ps", "-axo", "pid=,comm="], capture_output=True, text=True)
    if result.returncode != 0:
        raise BridgeError("Cannot inspect running apps; refusing to launch another instance")
    name = APPS[app]["name"]
    suffix = "/" + name + ".app/Contents/MacOS/" + name
    installed = executable(app)
    matches = []
    for line in result.stdout.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) != 2:
            continue
        try:
            pid = int(fields[0])
        except ValueError:
            continue
        binary = fields[1]
        if pid > 0 and (binary == installed or binary.endswith(suffix)):
            matches.append(pid)
    return matches


@contextmanager
def launch_lock(app):
    """Serialize starts for this user and app, even with different state roots."""
    LAUNCH_LOCK_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = LAUNCH_LOCK_DIR / (app + ".lock")
    fd = os.open(str(path), os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def inventory():
    found = []
    for app, spec in APPS.items():
        path = Path(executable(app))
        version = None
        if path.is_file():
            with (path.parents[1] / "Info.plist").open("rb") as stream:
                version = plistlib.load(stream).get("CFBundleShortVersionString")
        found.append({"app": app, "installed": path.is_file(), "version": version})
    return found


def read_reply(stream, request_id):
    # Bounded frames, and only accept the reply for this request.
    for _ in range(16):
        line = stream.readline(MAX_REPLY + 1)
        if not line:
            raise BridgeError("Control connection closed")
        if len(line) > MAX_REPLY or not line.endswith(b"\n"):
            raise BridgeError("Oversized or incomplete control reply")
        reply = json.loads(line)
        if not isinstance(reply, dict):
            raise BridgeError("Invalid control reply")
        if reply.get("id") == request_id:
            if reply.get("ok") is False or "error" in reply:
                raise BridgeError("App rejected request: {}".format(reply.get("error")))
            if "result" not in reply:
                raise BridgeError("Control reply has no result")
            return reply["result"]
    raise BridgeError("No matching control reply")


class DeadlineStream:
    """Bounded lines with one wall-clock deadline for the complete call."""
    def __init__(self, sock, deadline):
        self.sock = sock
        self.deadline = deadline
        self.pending = bytearray()

    def remaining(self):
        left = self.deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("Control request deadline exceeded")
        self.sock.settimeout(left)

    def write(self, frame):
        self.remaining()
        self.sock.sendall(frame)

    def flush(self):
        pass

    def readline(self, limit):
        while True:
            self.remaining()
            end = self.pending.find(b"\n")
            if end >= 0:
                if end + 1 > limit:
                    raise BridgeError("Oversized control reply")
                line = bytes(self.pending[:end + 1])
                del self.pending[:end + 1]
                return line
            if len(self.pending) >= limit:
                raise BridgeError("Oversized control reply")
            chunk = self.sock.recv(min(65536, limit - len(self.pending)))
            if not chunk:
                raise BridgeError("Connection closed; operation may have completed. Inspect before retrying")
            self.pending.extend(chunk)


def send(stream, request, request_id):
    frame = (json.dumps(request, separators=(",", ":")) + "\n").encode()
    if len(frame) > MAX_REQUEST:
        raise BridgeError("Request exceeds 1 MiB")
    stream.write(frame)
    stream.flush()
    return read_reply(stream, request_id)


def call(app, method, params=None, timeout=20, state=None, reload_document=False):
    params = {} if params is None else params
    if not isinstance(method, str) or not method or not isinstance(params, dict):
        raise BridgeError("Method must be a string and params a JSON object")
    if not 0 < timeout <= 55:
        raise BridgeError("Timeout must be greater than zero and at most 55 seconds")
    if state is None:
        runtime = RUNTIME / app
        runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
        with (runtime / "launch.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return call(app, method, params, timeout, state=load_state(app), reload_document=reload_document)
    if reload_document and (app != "cadcraft" or method != "app.open"):
        raise BridgeError("Document reload is supported only for CADCraft app.open")
    if app == "cadcraft" and method == "app.open":
        return _cad_open(params, timeout, state, reload_document)
    return _request(app, method, params, timeout, state)


def _cad_open(params, timeout, state, reload_document):
    """Serialize document discovery/mutation, including explicit-state callers."""
    runtime = RUNTIME / "cadcraft"
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (runtime / "documents.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _cad_open_unlocked(params, timeout, state, reload_document)


def _cad_open_unlocked(params, timeout, state, reload_document):
    raw = params.get("path")
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise BridgeError("CADCraft app.open requires an absolute file path")
    path = Path(raw).expanduser().resolve()
    params = dict(params, path=str(path))
    deadline = time.monotonic() + timeout
    def request(method, values):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BridgeError("Document operation deadline exceeded; inspect before retrying")
        return _request("cadcraft", method, values, remaining, state)
    inspected = request("ui.inspect", {})
    try:
        documents = inspected["session"]["documents"]
        if not isinstance(documents, list):
            raise ValueError()
        for doc in documents:
            if not isinstance(doc, dict) or type(doc.get("index")) is not int or doc["index"] < 0:
                raise ValueError()
            if type(doc.get("dirty")) is not bool or not isinstance(doc.get("path"), (str, type(None))):
                raise ValueError()
        if len({doc["index"] for doc in documents}) != len(documents):
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise BridgeError("Cannot inspect CADCraft documents; refusing a duplicate open")
    matches = [doc for doc in documents if doc.get("path") and Path(doc["path"]).resolve() == path]
    if matches and not reload_document:
        chosen = next((doc for doc in matches if doc.get("active")), matches[-1])
        result = request("engine.execute", {"command": "document.switch", "params": {"index": chosen["index"]}})
        return {"path": str(path), "reused": True, "index": chosen["index"], "reply": result}
    if reload_document and matches:
        if any(doc["dirty"] for doc in matches):
            raise BridgeError("Document has unsaved changes; refusing to reload")
        if not path.is_file():
            raise BridgeError("Reload source is missing; leaving saved tabs open")
        for doc in sorted(matches, key=lambda doc: doc["index"], reverse=True):
            request("engine.execute", {"command": "close", "params": {"index": doc["index"]}})
    return request("app.open", params)


def _request(app, method, params, timeout, state):
    spec = APPS[app]
    request_id = uuid.uuid4().hex
    envelope = {"id": request_id, "method": method, "params": params}
    if spec.get("rpc"):
        envelope["jsonrpc"] = "2.0"
    deadline = time.monotonic() + timeout
    try:
        sock = socket.create_connection(("127.0.0.1", state["port"]), timeout=timeout)
    except OSError as error:
        raise BridgeError("Connection failed; request was not sent: {}".format(error))
    with sock:
        stream = DeadlineStream(sock, deadline)
        try:
            if spec.get("auth") or spec.get("rpc"):
                token = Path(state["token_file"]).read_text().strip()
                if spec.get("rpc"):
                    token = json.loads(token)["token"]
                auth = {"id": "auth", "method": "auth", "params": {"token": token}}
                if spec.get("rpc"):
                    auth["jsonrpc"] = "2.0"
                send(stream, auth, "auth")
            return send(stream, envelope, request_id)
        except (OSError, ValueError) as error:
            # Never resend an edit after a transport failure.
            raise BridgeError("Reply failed; operation may have completed. Inspect before retrying: {}".format(error))


def start(app, portable_copy=False, allow_multiple=False):
    if platform.system() != "Darwin":
        raise BridgeError("Desktop launch is supported only on macOS")
    if app == "pdfcraft" and not portable_copy:
        raise BridgeError("PdfCraft isolation requires --portable-copy; this copies and ad-hoc signs a private bundle")
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "outputs").mkdir(exist_ok=True)
    spec = APPS[app]
    binary = executable(app)
    if not Path(binary).is_file():
        raise BridgeError("App is not installed: " + spec["name"])
    runtime = RUNTIME / app
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    with launch_lock(app), (runtime / "launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            state = load_state(app)
        except SessionConflict:
            raise
        except BridgeError:
            state = None
        if state:
            call(app, "ui.state" if spec.get("rpc") else "ui.inspect", state=state)
            return {"app": app, "pid": state["pid"], "port": state["port"], "reused": True}
        if not allow_multiple:
            existing = running_instances(app)
            if existing:
                raise SessionConflict(
                    "{} is already running (PIDs {}). Use the existing session's --state-dir, "
                    "or explicitly pass --allow-multiple for an isolated session. "
                    "Unknown instances are never adopted or stopped.".format(spec["name"], existing))
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        profile = runtime / ("profile-" + uuid.uuid4().hex[:12])
        profile.mkdir(mode=0o700)
        if app == "pdfcraft":
            bundle = profile / "PdfCraft.app"
            shutil.copytree(str(APPS_DIR / "PdfCraft.app"), str(bundle), symlinks=True)
            binary = str(bundle / "Contents" / "MacOS" / "PdfCraft")
            (Path(binary).parent / "PdfCraft.portable").touch(mode=0o600)
            (Path(binary).parent / "PdfCraftData").mkdir(mode=0o700)
            # Portable files alter the bundle seal. Sign only this private copy.
            subprocess.run(["xattr", "-cr", str(bundle)], check=True, capture_output=True)
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(bundle)],
                           check=True, capture_output=True)
        env = os.environ.copy()
        env[app.upper() + "_CONFIG_DIR"] = str(profile)
        if app == "lightcraft":
            env["LIGHTCRAFT_NO_PREFS"] = "1"
        cmd = [binary, "--control", str(port)]
        if app == "filmcraft":
            cmd += ["--data-dir", str(profile), "--empty", "--no-recover"]
        if app == "lightcraft":
            cmd += ["--memory", "--no-demo"]
        token_file = None
        if spec.get("rpc"):
            token_file = runtime / ("control-" + uuid.uuid4().hex + ".json")
            cmd = [binary, "--control", str(token_file)]
        elif spec.get("auth"):
            token_file = runtime / ("token-" + uuid.uuid4().hex)
            fd = os.open(str(token_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(secrets.token_hex(32))
            cmd += ["--control-token-file", str(token_file)]
        if spec.get("roots"):
            cmd += ["--automation-read-root", str(BASE),
                    "--automation-write-root", str(BASE / "outputs")]
        log = runtime / ("launch-" + uuid.uuid4().hex[:12] + ".log")
        with log.open("wb") as output:
            process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=output, env=env,
                                       cwd=str(BASE), start_new_session=True)
        state = {"app": app, "pid": process.pid, "port": port, "executable": binary,
                 "workspace": str(BASE), "apps_dir": str(APPS_DIR),
                 "process_identity": process_identity(process.pid),
                 "profile": str(profile), "log": str(log)}
        if token_file:
            state["token_file"] = str(token_file)
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise BridgeError("App exited during startup; see " + str(log))
            if spec.get("rpc"):
                try:
                    discovery = json.loads(token_file.read_text())
                    state["port"] = discovery["port"]
                except (FileNotFoundError, ValueError, KeyError):
                    time.sleep(0.1)
                    continue
            try:
                with socket.create_connection(("127.0.0.1", state["port"]), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        else:
            process.terminate()  # Only the app process this launch created.
            raise BridgeError("App control listener did not start; see " + str(log))
        atomic_json(state_path(app), state)
        result = call(app, "ui.state" if spec.get("rpc") else "ui.inspect", state=state)
        return {"app": app, "pid": state["pid"], "port": state["port"],
                "connected": True, "state_fields": list(result) if isinstance(result, dict) else []}


def stop(app, allow_empty_pdf_termination=False):
    runtime = RUNTIME / app
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (runtime / "launch.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return stop_locked(app, allow_empty_pdf_termination)


def stop_locked(app, allow_empty_pdf_termination=False):
    state = load_state(app)
    if app == "pdfcraft":
        if not allow_empty_pdf_termination:
            raise BridgeError("PdfCraft has no quit method; use its UI or explicitly pass --allow-empty-pdf-termination")
        current = call(app, "ui.state", state=state)
        if current.get("documents") != []:
            raise BridgeError("PdfCraft has open documents; close them before stopping")
        if not process_matches(app, state["pid"], state["executable"], state["process_identity"]):
            raise BridgeError("Managed process changed before stop")
        # This release has no quit command. Terminate only an empty owned session.
        os.kill(state["pid"], signal.SIGTERM)
        result = {}
    else:
        result = call(app, "app.quit", state=state)
    # A save prompt means the app is intentionally left open, never force-killed.
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if not process_matches(app, state["pid"], state.get("executable"), state.get("process_identity")):
            state_path(app).unlink(missing_ok=True)
            return {"app": app, "stopped": True}
        time.sleep(0.1)
    return {"app": app, "stopped": False, "reply": result,
            "note": "App remains open; inspect any save prompt"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("--workspace", help="Documents workspace (default: current directory)")
    parser.add_argument("--state-dir", help="Private runtime state directory")
    parser.add_argument("--apps-dir", help="Directory containing ArtCraft .app bundles")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("inventory")
    for action in ("start", "stop", "inspect", "commands"):
        p = sub.add_parser(action)
        p.add_argument("app", choices=APPS)
        if action == "start":
            p.add_argument("--allow-multiple", action="store_true", help="Explicitly allow another isolated instance of an already running app")
            p.add_argument("--portable-copy", action="store_true", help="Opt in to copying and locally signing PdfCraft")
        if action == "stop":
            p.add_argument("--allow-empty-pdf-termination", action="store_true", help="Allow SIGTERM only for an empty managed PdfCraft")
    p = sub.add_parser("cad-export-stl", help="Export a convex closed CADCraft triangular face mesh as STL")
    p.add_argument("--units", choices=["mm"], required=True)
    p.add_argument("--name", default="cadcraft-solid")
    p = sub.add_parser("cad-extrude", help="Extrude a CADCraft convex profile into bridge-owned STL and 3DFACE DXF")
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--units", choices=["mm"], required=True, help="Explicitly interpret source coordinates as millimetres")
    p.add_argument("--handle", help="Source entity handle; required if drawing contains more than one entity")
    p.add_argument("--name", default="extrusion")
    p = sub.add_parser("open-document", help="Open or activate a CADCraft document in its existing managed session")
    p.add_argument("app", choices=["cadcraft"])
    p.add_argument("path", type=Path)
    p.add_argument("--reload", action="store_true", help="Reload from disk after closing saved matching tabs; refuse unsaved changes")
    p = sub.add_parser("call")
    p.add_argument("app", choices=APPS)
    p.add_argument("method")
    p.add_argument("params", nargs="?", default=None)
    p.add_argument("--params-file", type=Path, help="Read params JSON object from a file")
    p.add_argument("--timeout", type=float, default=20)
    p.add_argument("--reload-document", action="store_true", help="Explicit reload for CADCraft app.open only")
    args = parser.parse_args()
    configure(args.workspace, args.state_dir, args.apps_dir)
    try:
        if args.action == "open-document":
            result = call(args.app, "app.open", {"path": str(args.path.expanduser().resolve())}, reload_document=args.reload)
        elif args.action == "cad-export-stl":
            from .solid import export_stl
            drawing = call("cadcraft", "drawing.inspect", {"entities": True, "limit": 10000})
            result = export_stl(drawing, BASE / "outputs", args.name)
        elif args.action == "cad-extrude":
            from .solid import export_extrusion
            drawing = call("cadcraft", "drawing.inspect", {"entities": True, "limit": 10000})
            if len(drawing.get("entities", [])) != drawing.get("entityCount"):
                raise BridgeError("Drawing inspection is truncated; use a smaller drawing")
            result = export_extrusion(drawing, args.height, BASE / "outputs", args.name, args.handle)
        elif args.action == "inventory":
            result = inventory()
        elif args.action == "start":
            result = start(args.app, args.portable_copy, args.allow_multiple)
        elif args.action == "stop":
            result = stop(args.app, args.allow_empty_pdf_termination)
        elif args.action == "inspect":
            result = call(args.app, "ui.state" if APPS[args.app].get("rpc") else "ui.inspect")
        elif args.action == "commands":
            result = call(args.app, "ui.commands" if APPS[args.app].get("rpc") else "engine.commands")
        else:
            if args.params is not None and args.params_file is not None:
                raise BridgeError("Use either positional JSON or --params-file, not both")
            raw = args.params_file.read_text() if args.params_file is not None else (args.params if args.params is not None else "{}")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise BridgeError("Params must be a JSON object")
            result = call(args.app, args.method, parsed, args.timeout, reload_document=args.reload_document)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (BridgeError, OSError, ValueError, subprocess.CalledProcessError, KeyError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
