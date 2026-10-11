"""Create and verify a 40 mm 3D wireframe cube in CADCraft 0.5.0.

Requires installed ArtCraft Bridge and CADCraft. Writes DXF, PNG and a concise
verification report; does not publish app state or tokens.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from artcraft_bridge import bridge


def cube_edges(size=40.0):
    """Rotate orthogonal cube axes for a readable XY orthographic preview."""
    c, s = math.cos(math.pi / 6), math.sin(math.pi / 6)
    axes = [(c * c, s * c, -s),
            (c * s * s - s * c, s * s * s + c * c, c * s),
            (c * s * c + s * s, s * s * c - c * s, c * c)]
    vertices = {}
    for bits in range(8):
        vertices[bits] = [round(size * sum(axes[a][d] for a in range(3)
                                        if bits & (1 << a)), 9) for d in range(3)]
    return [(vertices[i], vertices[i | (1 << axis)], axis)
            for axis in range(3) for i in range(8) if not i & (1 << axis)]


def verify_drawing(state, size=40.0):
    entities = state.get("entities", [])
    if state.get("entityCount") != 12 or len(entities) != 12:
        raise ValueError("Expected exactly twelve 3D polyline entities")
    degrees = Counter()
    lengths = []
    actual_edges = set()
    for entity in entities:
        geometry = entity.get("geometry", {})
        if geometry.get("type") != "polyline3d" or len(geometry.get("points", [])) != 2:
            raise ValueError("Every edge must be a two-point 3D polyline")
        points = [tuple(round(point[axis], 6) for axis in ("x", "y", "z"))
                  for point in geometry["points"]]
        length = math.dist(*points)
        if not math.isclose(length, size, abs_tol=2e-6):
            raise ValueError("Unexpected edge length")
        lengths.append(length)
        degrees.update(points)
        actual_edges.add(tuple(sorted(points)))
    expected_edges = {tuple(sorted(tuple(round(v, 6) for v in point) for point in (a, b)))
                      for a, b, _ in cube_edges(size)}
    if actual_edges != expected_edges or len(degrees) != 8 or set(degrees.values()) != {3}:
        raise ValueError("Geometry does not match the intended cube")
    z_values = {point[2] for point in degrees}
    if len(z_values) < 2:
        raise ValueError("Z coordinates were flattened")
    return {"entities": 12, "entity_type": "3D Polyline", "vertices": 8,
            "edge_length_mm": size, "distinct_z_planes": len(z_values),
            "vertex_degree": 3, "min_edge_length": min(lengths),
            "max_edge_length": max(lengths), "geometry_verified": True}


def run(workspace, state_dir=None):
    workspace = Path(workspace).expanduser().resolve()
    output = workspace / "outputs"
    output.mkdir(parents=True, exist_ok=True)
    dxf = output / "artcraft-cube-40.dxf"
    png = output / "artcraft-cube-40.png"
    report_path = output / "cadcraft-cube-verification.json"
    if any(path.exists() for path in (dxf, png, report_path)):
        raise ValueError("Example output already exists; use a fresh workspace")
    bridge.configure(workspace=workspace, state_dir=state_dir)
    started = bridge.start("cadcraft")
    if started.get("reused"):
        raise ValueError("Example requires a fresh managed CADCraft session; stop the existing session first")

    def execute(command, params):
        return bridge.call("cadcraft", "engine.execute", {"command": command, "params": params})

    execute("new", {"metric": True})
    for a, b, axis in cube_edges():
        execute("color", {"color": (1, 3, 5)[axis]})
        execute("3dpoly", {"points": [a, b]})
    execute("zoom.extents", {})
    inspect = {"entities": True, "limit": 100}
    before = verify_drawing(bridge.call("cadcraft", "drawing.inspect", inspect))
    bridge.call("cadcraft", "app.save", {"path": str(dxf)})
    bridge.call("cadcraft", "app.open", {"path": str(dxf)}, reload_document=True)
    after = verify_drawing(bridge.call("cadcraft", "drawing.inspect", inspect))
    render = bridge.call("cadcraft", "ui.render", {"path": str(png), "width": 1400,
                                                   "height": 1000, "fit": True})
    report = {"app": "CADCraft", "app_version": next(row["version"] for row in bridge.inventory()
              if row["app"] == "cadcraft"), "before_save": before, "after_reopen": after,
              "dxf_reopened": True, "files": {"drawing": dxf.name, "preview": png.name},
              "render": {"width": render["width"], "height": render["height"]},
              "model_kind": "3D wireframe, not a solid or a surface mesh"}
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    # Leave the saved drawing visible for inspection. Stop explicitly when done.
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    run(args.workspace, args.state_dir)
