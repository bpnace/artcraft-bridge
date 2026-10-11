"""Bridge-owned convex extrusion and closed triangle mesh export; no CAD kernel."""
from collections import Counter
import math
from pathlib import Path


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def profile(drawing, handle=None):
    entities = drawing.get('entities', [])
    if handle is not None:
        entities = [e for e in entities if e.get('handle') == handle]
    if len(entities) != 1:
        raise ValueError('Choose exactly one profile entity with --handle')
    g = entities[0]['geometry']
    if g.get('type') != 'lwPolyline' or not g.get('closed'):
        raise ValueError('Requires one closed straight lightweight polyline')
    vertices = g['vertices']
    if any(v.get('bulge', 0) or v.get('start_width', 0) or v.get('end_width', 0) for v in vertices) or g.get('const_width', 0):
        raise ValueError('Curved or wide polylines are unsupported')
    points = [(float(v['p']['x']), float(v['p']['y'])) for v in vertices]
    return points, float(g.get('elevation', 0)), entities[0]['handle']


def extrude(points, height, elevation=0):
    points = [tuple(map(float, p)) for p in points]
    height, elevation = float(height), float(elevation)
    if not 3 <= len(points) <= 1024 or any(len(p) != 2 for p in points):
        raise ValueError('Profile requires 3 to 1024 XY vertices')
    if not all(math.isfinite(v) for p in points for v in p) or not math.isfinite(height) or not math.isfinite(elevation) or height <= 0:
        raise ValueError('Coordinates must be finite and height must be positive')
    if len(set(points)) != len(points):
        raise ValueError('Duplicate vertices are unsupported')
    shifted = [(x-points[0][0], y-points[0][1]) for x,y in points]
    area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(shifted, shifted[1:]+shifted[:1])) / 2
    if area < 0:
        points.reverse()
        area = -area
    scale = max(max(p[i] for p in points)-min(p[i] for p in points) for i in (0,1))
    tolerance = max(scale*scale*1e-12, 1e-12)
    # Every non-edge vertex must lie strictly left of every oriented edge.
    # This excludes concavity, collinear edges and self-intersecting star polygons.
    for i,a in enumerate(points):
        b = points[(i+1)%len(points)]
        for j,p in enumerate(points):
            if j not in (i,(i+1)%len(points)) and (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]) <= tolerance:
                raise ValueError('Only simple strictly convex profiles are supported')
    lower = [(x,y,elevation) for x,y in points]
    upper = [(x,y,elevation+height) for x,y in points]
    triangles = []
    for i in range(1,len(points)-1):
        triangles.extend([(lower[0],lower[i+1],lower[i]), (upper[0],upper[i],upper[i+1])])
    for i in range(len(points)):
        j=(i+1)%len(points)
        triangles.extend([(lower[i],lower[j],upper[j]),(lower[i],upper[j],upper[i])])
    report = verify_mesh(triangles)
    if not math.isclose(report['volume'], area*height, rel_tol=1e-9, abs_tol=1e-8):
        raise ValueError('Mesh volume differs from profile area times height')
    return triangles, report


def verify_mesh(triangles):
    edges = Counter()
    vertices = set()
    volume = 0.0
    origin = triangles[0][0] if triangles else (0,0,0)
    for a,b,c in triangles:
        if not all(len(p)==3 and all(math.isfinite(v) for v in p) for p in (a,b,c)):
            raise ValueError('Invalid triangle coordinates')
        normal = cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))
        if sum(v*v for v in normal) == 0:
            raise ValueError('Degenerate triangle')
        vertices.update((a,b,c))
        for x,y in ((a,b),(b,c),(c,a)): edges[(x,y)] += 1
        shifted = [tuple(p[i]-origin[i] for i in range(3)) for p in (a,b,c)]
        volume += sum(shifted[0][i]*cross(shifted[1],shifted[2])[i] for i in range(3))/6
    if not triangles or any(count != 1 or edges[(b,a)] != 1 for (a,b),count in edges.items()):
        raise ValueError('Mesh is not closed with consistent outward winding')
    if volume <= 0 or not math.isfinite(volume):
        raise ValueError('Mesh must enclose positive volume')
    # Limit this exporter to convex closed boundaries, avoiding self-intersecting soups.
    scale = max(max(p[i] for p in vertices)-min(p[i] for p in vertices) for i in range(3))
    for a,b,c in triangles:
        n=cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))
        tolerance = max(scale,1.0)*math.sqrt(sum(v*v for v in n))*1e-9
        if any(sum(n[i]*(p[i]-a[i]) for i in range(3)) > tolerance for p in vertices):
            raise ValueError("Only convex outward-oriented mesh boundaries are supported")
    return {'triangles':len(triangles),'vertices':len(vertices),'watertight':True,
            'consistent_winding':True,'volume':volume,
            'bounds':[[min(p[i] for p in vertices) for i in range(3)],
                      [max(p[i] for p in vertices) for i in range(3)]]}


def stl_text(triangles):
    verify_mesh(triangles)
    lines=['solid artcraft_bridge']
    for a,b,c in triangles:
        n=cross(tuple(b[i]-a[i] for i in range(3)),tuple(c[i]-a[i] for i in range(3)))
        length=math.sqrt(sum(v*v for v in n))
        lines.append('  facet normal '+' '.join(format(v/length,'.17g') for v in n))
        lines.append('    outer loop')
        lines.extend('      vertex '+' '.join(format(v,'.17g') for v in p) for p in (a,b,c))
        lines.extend(['    endloop','  endfacet'])
    return '\n'.join(lines+['endsolid artcraft_bridge',''])


def dxf_text(triangles):
    verify_mesh(triangles)
    lines=['0','SECTION','2','HEADER','9','$INSUNITS','70','4','0','ENDSEC','0','SECTION','2','ENTITIES']
    for triangle in triangles:
        lines.extend(['0','3DFACE','8','0'])
        for i,p in enumerate((*triangle, triangle[2])):
            for axis,value in enumerate(p): lines.extend([str(10+i+axis*10),format(value,'.17g')])
    return '\n'.join(lines+['0','ENDSEC','0','EOF',''])


def export_extrusion(drawing, height, directory, name='extrusion', handle=None):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise ValueError('Name must contain only letters, digits, underscore or hyphen')
    points,elevation,source_handle = profile(drawing,handle)
    triangles,report = extrude(points,height,elevation)
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=True)
    files={suffix:directory/(name+'.'+suffix) for suffix in ('stl','dxf')}
    if any(p.exists() for p in files.values()): raise ValueError('Output already exists; choose a new name')
    created=[]
    try:
        for suffix,text in [('stl',stl_text(triangles)),('dxf',dxf_text(triangles))]:
            with files[suffix].open('x',encoding='ascii') as f:
                created.append(files[suffix]); f.write(text)
    except OSError:
        for p in created: p.unlink(missing_ok=True)
        raise
    return dict(report,source_handle=source_handle,units='mm',backend='bridge convex extrusion mesh',
                files={k:p.name for k,p in files.items()})


def triangles_from_drawing(drawing):
    triangles=[]
    entities=drawing.get('entities',[])
    if len(entities) != drawing.get('entityCount'):
        raise ValueError('Drawing inspection is truncated')
    for entity in entities:
        g=entity['geometry']
        if g.get('type') != 'face3d': raise ValueError('Drawing must contain only triangular 3DFACE entities')
        corners=[tuple(float(p[a]) for a in ('x','y','z')) for p in g['corners']]
        if len(corners)!=4 or corners[2]!=corners[3]: raise ValueError('Requires triangular faces, not quads')
        triangles.append(tuple(corners[:3]))
    verify_mesh(triangles)
    return triangles


def export_stl(drawing, directory, name='cadcraft-solid'):
    if not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
        raise ValueError('Invalid output name')
    triangles=triangles_from_drawing(drawing)
    report=verify_mesh(triangles)
    path=Path(directory)/(name+'.stl')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='ascii') as stream: stream.write(stl_text(triangles))
    return dict(report,units='mm',backend='bridge STL writer from CADCraft 3DFACE readback',file=path.name)
