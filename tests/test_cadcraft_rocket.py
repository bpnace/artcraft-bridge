import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('rocket_example', Path(__file__).parents[1] / 'examples/cadcraft_rocket.py')
rocket = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rocket)


class RocketTests(unittest.TestCase):
    def test_connected_closed_rocket_dimensions(self):
        r = rocket.verify_rocket(rocket.rocket_triangles())
        self.assertEqual(r['triangles'], 2560)
        self.assertEqual(r['vertices'], 1282)
        self.assertEqual(r['bounds_mm'], [[-32.0, -32.0, 0.0], [32.0, 32.0, 112.0]])
        self.assertEqual(r['connected_components'], 1)
        self.assertAlmostEqual(r['volume_mm3'], 53389.16254078238, places=6)

    def test_missing_or_reversed_face_rejected(self):
        t = rocket.rocket_triangles()
        for bad in [t[1:], [tuple(reversed(t[0]))] + t[1:]]:
            with self.assertRaises(ValueError): rocket.verify_rocket(bad)

    def test_serialization_and_no_stl_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            dxf, stl = Path(temp)/'rocket.dxf', Path(temp)/'rocket.stl'
            t = rocket.rocket_triangles()
            rocket.write_dxf(t, dxf); rocket.write_stl(t, stl)
            self.assertEqual(dxf.read_text().count('\n3DFACE\n'), 2560)
            self.assertEqual(stl.read_text().count('facet normal'), 2560)
            with self.assertRaises(FileExistsError): rocket.write_stl(t, stl)
