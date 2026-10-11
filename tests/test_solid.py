"""Geometry and serialization checks for the bridge convex mesh path."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
from artcraft_bridge import solid

RECTANGLE=[(0,0),(40,0),(40,30),(0,30)]


def drawing(points=RECTANGLE):
    return {'entityCount':1,'entities':[{'handle':'100','geometry':{
        'type':'lwPolyline','closed':True,'vertices':[{'p':{'x':x,'y':y},'bulge':0} for x,y in points]}}]}


class SolidTests(unittest.TestCase):
    def test_rectangle_volume_and_bounds(self):
        triangles,r=solid.extrude(RECTANGLE,20)
        self.assertEqual(r['volume'],24000)
        self.assertEqual(r['triangles'],12)
        self.assertEqual(r['bounds'],[[0,0,0],[40,30,20]])
        self.assertTrue(r['watertight'])

    def test_large_translation_preserves_volume(self):
        _,r=solid.extrude([(x+1e9,y+1e9) for x,y in RECTANGLE],20,1e9)
        self.assertAlmostEqual(r["volume"],24000)

    def test_clockwise_and_elevation(self):
        _,r=solid.extrude(list(reversed(RECTANGLE)),20,5)
        self.assertEqual(r['volume'],24000)
        self.assertEqual(r['bounds'][0][2],5)

    def test_triangle_profile(self):
        _,r=solid.extrude([(0,0),(10,0),(0,10)],7)
        self.assertAlmostEqual(r['volume'],350)
        self.assertEqual(r['triangles'],8)

    def test_bad_profiles(self):
        for points in [[(0,0),(1,0),(2,0)],[(0,0),(1,1),(0,1),(1,0)],
                       [(0,0),(2,0),(1,.2),(2,2),(0,2)],RECTANGLE+[RECTANGLE[0]],
                       [(0,0),(math.nan,0),(0,1)]]:
            with self.subTest(points=points),self.assertRaises(ValueError): solid.extrude(points,20)

    def test_invalid_height(self):
        for height in [0,-1,math.inf,math.nan]:
            with self.subTest(height=height),self.assertRaises(ValueError): solid.extrude(RECTANGLE,height)

    def test_open_and_wrong_winding(self):
        triangles,_=solid.extrude(RECTANGLE,20)
        for bad in [triangles[:-1],[tuple(reversed(t)) for t in triangles],triangles+[triangles[0]]]:
            with self.assertRaises(ValueError): solid.verify_mesh(bad)

    def test_stl_serialized_geometry(self):
        triangles,_=solid.extrude(RECTANGLE,20)
        text=solid.stl_text(triangles)
        points=[tuple(map(float,line.split()[1:])) for line in text.splitlines() if line.strip().startswith('vertex ')]
        readback=[tuple(points[i:i+3]) for i in range(0,len(points),3)]
        self.assertEqual(readback,triangles)
        self.assertEqual(solid.verify_mesh(readback)['volume'],24000)

    def test_dxf_xyz_and_triangle_marker(self):
        triangles,_=solid.extrude(RECTANGLE,20)
        pairs=list(zip(*[iter(solid.dxf_text(triangles).splitlines())]*2))
        entities=[]
        for code,value in pairs:
            if (code,value)==('0','3DFACE'): entities.append({})
            elif entities and code!='0': entities[-1][code]=value
        self.assertEqual(len(entities),12)
        for entity,triangle in zip(entities,triangles):
            for i,p in enumerate((*triangle,triangle[2])):
                self.assertEqual(tuple(float(entity[str(10+i+axis*10)]) for axis in range(3)),p)

    def test_curve_open_width_and_ambiguous_rejected(self):
        for kind in ['open','curve','width','ambiguous']:
            d=drawing()
            if kind=='open':d['entities'][0]['geometry']['closed']=False
            elif kind=='curve':d['entities'][0]['geometry']['vertices'][0]['bulge']=1
            elif kind=='width':d['entities'][0]['geometry']['const_width']=2
            else:d['entities'].append(copy.deepcopy(d['entities'][0]))
            with self.assertRaises(ValueError):solid.profile(d)

    def test_export_no_overwrite_and_safe_name(self):
        with tempfile.TemporaryDirectory() as out:
            report=solid.export_extrusion(drawing(),20,out,'block')
            self.assertEqual(report['volume'],24000)
            original=(Path(out)/'block.stl').read_bytes()
            with self.assertRaises(ValueError):solid.export_extrusion(drawing(),20,out,'block')
            with self.assertRaises(ValueError):solid.export_extrusion(drawing(),20,out,'../bad')
            self.assertEqual((Path(out)/'block.stl').read_bytes(),original)

    def test_face_readback_and_stl(self):
        triangles,_=solid.extrude(RECTANGLE,20)
        d={'entityCount':12,'entities':[{'geometry':{'type':'face3d','corners':[dict(zip(('x','y','z'),p)) for p in (*t,t[2])]}} for t in triangles]}
        self.assertEqual(solid.triangles_from_drawing(d),triangles)
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(solid.export_stl(d,out)['volume'],24000)
        d['entityCount']=13
        with self.assertRaises(ValueError):solid.triangles_from_drawing(d)
