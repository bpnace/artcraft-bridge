"""Geometry verification tests; real CADCraft exercise is documented separately."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cube', Path(__file__).resolve().parents[1] / 'examples/cadcraft_cube.py')
cube = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cube)


def synthetic_drawing():
    entities = []
    for a, b, _ in cube.cube_edges():
        entities.append({'geometry': {'type': 'polyline3d', 'points': [dict(zip(('x','y','z'), p)) for p in (a,b)]}})
    return {'entityCount': len(entities), 'entities': entities}


class CubeTests(unittest.TestCase):
    def test_reused_session_is_rejected_before_editing(self):
        with tempfile.TemporaryDirectory() as workspace:
            with patch.object(cube.bridge, "configure"), patch.object(cube.bridge, "start", return_value={"reused": True}), patch.object(cube.bridge, "call") as call:
                with self.assertRaisesRegex(ValueError, "fresh managed"):
                    cube.run(workspace)
                call.assert_not_called()

    def test_valid_cube(self):
        result = cube.verify_drawing(synthetic_drawing())
        self.assertEqual(result['vertices'], 8)
        self.assertEqual(result['entities'], 12)
        self.assertEqual(result['distinct_z_planes'], 8)

    def test_flattened_export_is_rejected(self):
        drawing = synthetic_drawing()
        for entity in drawing['entities']:
            for point in entity['geometry']['points']:
                point['z'] = 0
        with self.assertRaises(ValueError):
            cube.verify_drawing(drawing)

    def test_wrong_entity_type_is_rejected(self):
        drawing = synthetic_drawing()
        drawing['entities'][0]['geometry']['type'] = 'line'
        with self.assertRaises(ValueError):
            cube.verify_drawing(drawing)

    def test_missing_edge_is_rejected(self):
        drawing = synthetic_drawing()
        drawing['entities'].pop()
        drawing['entityCount'] -= 1
        with self.assertRaises(ValueError):
            cube.verify_drawing(drawing)

    def test_duplicate_edge_is_rejected(self):
        drawing = synthetic_drawing()
        drawing['entities'][-1] = drawing['entities'][0]
        with self.assertRaises(ValueError):
            cube.verify_drawing(drawing)


if __name__ == '__main__':
    unittest.main()
