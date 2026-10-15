"""Check map projection against independent geometric examples."""
import math
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from convert_small_city import pose, hull, clipped_xy

class CityGeometryTests(unittest.TestCase):
    def test_pose_rotates_then_translates(self):
        result=pose(f"10 20 0 0 0 {math.pi/2}") @ np.array([2,0,0,1])
        np.testing.assert_allclose(result,[10,22,0,1],atol=1e-12)

    def test_overhead_triangles_do_not_block_road(self):
        triangles=np.array([[[0,0,4],[2,0,4],[0,2,4]]],dtype=float)
        self.assertEqual(clipped_xy(triangles),[])

    def test_triangle_is_clipped_to_height_band(self):
        triangles=np.array([[[0,0,0],[4,0,4],[0,4,4]]],dtype=float)
        polygon=clipped_xy(triangles,1,2)
        self.assertEqual(set(polygon),{(1.,0.),(2.,0.),(0.,2.),(0.,1.)})

    def test_hull_discards_internal_and_duplicate_points(self):
        self.assertEqual(len(hull([(0,0),(2,0),(2,2),(0,2),(1,1),(0,0)])),4)
