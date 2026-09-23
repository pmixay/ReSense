"""ReSense — obstacle detection inside the train clearance gauge from 3D LiDAR.

Coordinate convention used everywhere inside the package ("vehicle frame", REP-103):
    X — forward along the track, Y — left, Z — up.
The raw Hesai sensor frame of the hackathon bags is converted with
:func:`resense.frame.sensor_to_vehicle` (sensor -y is forward, +x is left, +z is up).
"""

from resense.config import DetectorConfig
from resense.detector import Detector, FrameResult, Detection

__all__ = ["DetectorConfig", "Detector", "FrameResult", "Detection"]
__version__ = "0.6.3"
