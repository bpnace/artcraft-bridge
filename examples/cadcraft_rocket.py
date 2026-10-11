"""Create a nonconvex rocket mesh, roundtrip CADCraft faces, export STL.

Standard library only. This separate example does not broaden the convex CLI
exporter. CADCraft stores the faces; this script constructs the mesh and STL.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from artcraft_bridge import bridge
from artcraft_bridge.solid import cross


def rocket_triangles():
    count = 128
    sections = [(0, 8, 0), (3, 8, 0), (8, 6, 0), (12, 14, 18),
                (17, 14, 18), (42, 14, 0), (72, 14, 0), (82, 14, 0),
                (92, 10, 0), (102, 5, 0)]
    rings = []
    for z, radius, fin in sections:
        ring = []
        for j in range(count):
            angle = 2 * math.pi * j / count
            distance = abs((angle + math.pi / 4) % (math.pi / 2) - math.pi / 4)
            bump = max(0, 1 - distance / (2 * math.pi / count))
            r = radius + fin * bump
            ring.append((r * math.cos(angle), r * math.sin(angle), float(z)))
        rings.append(ring)
    triangles = []
    for lower, upper in zip(rings, rings[1:]):
        for j in range(count):
            k = (j + 1) % count
            triangles.extend([(lower[j], lower[k], upper[k]),
                              (lower[j], upper[k], upper[j])])
    for j in range(count):
        k = (j + 1) % count
        triangles.extend([((0.0, 0.0, 0.0), rings[0][k], rings[0][j]),
                          (rings[-1][j], rings[-1][k], (0.0, 0.0, 112.0))])
    return triangles


def verify_rocket(triangles):
    """Topology checks for this generated radial boundary, not a CAD kernel."""
    directed, vertices, adjacent = Counter(), set(), {}
    volume = 0.0
    for a, b, c in triangles:
        if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in (a, b, c)):
            raise ValueError('Invalid coordinates')
        n = cross(tuple(b[i] - a[i] for i in range(3)),
                  tuple(c[i] - a[i] for i in range(3)))
        if sum(v * v for v in n) == 0:
            raise ValueError('Degenerate triangle')
        vertices.update((a, b, c))
        for x, y in ((a, b), (b, c), (c, a)):
            directed[x, y] += 1
            adjacent.setdefault(x, set()).add(y)
            adjacent.setdefault(y, set()).add(x)
        volume += sum(a[i] * cross(b, c)[i] for i in range(3)) / 6
    if not triangles or any(n != 1 or directed[y, x] != 1 for (x, y), n in directed.items()):
        raise ValueError('Mesh is not closed with consistent winding')
    unseen = set(vertices)
    parts = 0
    while unseen:
        parts += 1
        pending = [unseen.pop()]
        while pending:
            for v in adjacent[pending.pop()]:
                if v in unseen:
                    unseen.remove(v)
                    pending.append(v)
    euler = len(vertices) - len(directed) // 2 + len(triangles)
    if parts != 1 or euler != 2 or volume <= 0:
        raise ValueError('Expected one outward closed rocket boundary')
    return {'triangles': len(triangles), 'vertices': len(vertices),
            'watertight': True, 'consistent_winding': True,
            'connected_components': parts, 'euler_number': euler,
            'volume_mm3': volume, 'units': 'mm',
            'bounds_mm': [[min(p[i] for p in vertices) for i in range(3)],
                          [max(p[i] for p in vertices) for i in range(3)]]}


def write_dxf(triangles, path):
    lines = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4',
             '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    for a, b, c in triangles:
        lines.extend(['0', '3DFACE', '8', 'ROCKET'])
        for i, p in enumerate((a, b, c, c)):
            for axis, value in enumerate(p):
                lines.extend([str(10 + i + axis * 10), format(value, '.17g')])
    path.write_text('\n'.join(lines + ['0', 'ENDSEC', '0', 'EOF', '']), encoding='ascii')


def write_stl(triangles, path):
    lines = ['solid orbit_01']
    for a, b, c in triangles:
        n = cross(tuple(b[i] - a[i] for i in range(3)),
                  tuple(c[i] - a[i] for i in range(3)))
        length = math.sqrt(sum(v * v for v in n))
        lines.append('  facet normal ' + ' '.join(format(v / length, '.17g') for v in n))
        lines.append('    outer loop')
        lines.extend('      vertex ' + ' '.join(format(v, '.17g') for v in p) for p in (a, b, c))
        lines.extend(['    endloop', '  endfacet'])
    with path.open('x', encoding='ascii') as stream:
        stream.write('\n'.join(lines + ['endsolid orbit_01', '']))


def run(workspace, state_dir=None, allow_multiple=False):
    workspace = Path(workspace).expanduser().resolve()
    out = workspace / 'outputs'
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use a fresh workspace with empty outputs')
    bridge.configure(workspace=workspace, state_dir=state_dir)
    started = bridge.start('cadcraft', allow_multiple=allow_multiple)
    if started.get('reused'):
        raise ValueError('Example requires a fresh managed session')
    triangles = rocket_triangles()
    verify_rocket(triangles)
    write_dxf(triangles, out / 'rocket-source.dxf')
    bridge.call('cadcraft', 'app.open', {'path': str(out / 'rocket-source.dxf')})
    bridge.call('cadcraft', 'app.save', {'path': str(out / 'rocket-cadcraft.dxf')})
    bridge.call('cadcraft', 'app.open', {'path': str(out / 'rocket-cadcraft.dxf')}, reload_document=True)
    drawing = bridge.call('cadcraft', 'drawing.inspect', {'entities': True, 'limit': 10000})
    if len(drawing.get('entities', [])) != drawing.get('entityCount'):
        raise ValueError('Truncated CADCraft readback')
    reopened = []
    for entity in drawing['entities']:
        g = entity['geometry']
        if g.get('type') != 'face3d':
            raise ValueError('Expected triangular faces')
        corners = [tuple(float(p[a]) for a in ('x', 'y', 'z')) for p in g['corners']]
        if len(corners) != 4 or corners[2] != corners[3]:
            raise ValueError('Expected triangular 3DFACE')
        reopened.append(tuple(corners[:3]))
    if reopened != triangles:
        raise ValueError('CADCraft changed the rocket mesh during save/reopen')
    report = verify_rocket(reopened)
    write_stl(reopened, out / 'rocket.stl')
    bridge.call('cadcraft', 'engine.execute', {'command': 'zoom.extents', 'params': {}})
    report.update(model='ORBIT / 01', height_mm=112, hull_diameter_mm=28,
                  fin_span_mm=64, fins=4, native_brep=False,
                  cadcraft_save_reopen_identical=True,
                  pipeline='Example radial mesh -> CADCraft faces -> save/reopen/readback -> example STL')
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--state-dir', type=Path)
    parser.add_argument('--allow-multiple', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.workspace, args.state_dir, args.allow_multiple), indent=2))
