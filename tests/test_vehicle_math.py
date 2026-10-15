"""Independent kinematic checks for the simulator navigation adapter."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2_ws/src/agile_navigation/scripts'))
from vehicle_math import curvature_from_front_angles, steering_from_twist, integrate, footprint_overlaps_box, footprint_overlaps_polygon


class VehicleMathTests(unittest.TestCase):
    def test_ackermann_wheel_angles_recover_known_circle(self):
        radius,wheelbase,track=4.0,1.75,1.2
        left=math.atan(wheelbase/(radius-track/2))
        right=math.atan(wheelbase/(radius+track/2))
        self.assertAlmostEqual(curvature_from_front_angles(left,right,wheelbase,track),1/radius)

    def test_quarter_circle_integration(self):
        x,y,yaw=integrate(0,0,0,1,.25,2*math.pi)
        self.assertAlmostEqual(x,4)
        self.assertAlmostEqual(y,4)
        self.assertAlmostEqual(yaw,math.pi/2)

    def test_no_in_place_steering_and_bounded_angle(self):
        self.assertEqual(steering_from_twist(0,1,1.75,.48),0)
        self.assertEqual(steering_from_twist(.1,2,1.75,.48),.48)
        self.assertEqual(steering_from_twist(.1,-2,1.75,.48),-.48)

    def test_rotated_footprint_overlap(self):
        self.assertTrue(footprint_overlaps_box(0,0,math.pi/2,[0,1.5],[1,1,2]))
        self.assertFalse(footprint_overlaps_box(0,0,math.pi/2,[3,0],[1,1,2]))

    def test_convex_city_obstacle_overlap(self):
        triangle=[(2,-1),(4,0),(2,1)]
        self.assertFalse(footprint_overlaps_polygon(0,0,0,triangle))
        self.assertTrue(footprint_overlaps_polygon(1,0,0,triangle))
        self.assertTrue(footprint_overlaps_polygon(2,0,math.pi/2,triangle))

    def test_reverse_circle_is_consistent(self):
        x,y,yaw=integrate(0,0,0,-1,-.25,2*math.pi)
        self.assertAlmostEqual(x,-4)
        self.assertAlmostEqual(y,4)
        self.assertAlmostEqual(yaw,-math.pi/2)


if __name__=='__main__':
    unittest.main()
