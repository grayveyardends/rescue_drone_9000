import cv2
from collections import deque
from dataclasses import dataclass
from typing import Optional
import numpy as np
import base64

@dataclass
class SpatialFrame:
    frame: np.ndarray
    timestamp: float
    frame_id: int
    gps: tuple
    motion_score: float

class SpacialCV:
    def __init__(self, source=0, buffer_size=32):
        self.cap = cv2.VideoCapture(source)
        self.ring = deque(maxlen=buffer_size)
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50
        )
        self.frame_id = 0

    def read(self, gps=(0,0,0)):
        ret, frame = self.cap.read()
        if not ret:
            return None
        mask = self.bg_sub.apply(frame)
        motion = np.sum(mask > 0) / mask.size  # 0.0 - 1.0
        sf = SpatialFrame(
            frame=frame,
            timestamp=time.time(),
            frame_id=self.frame_id,
            gps=gps,
            motion_score=motion
        )
        self.ring.append(sf)
        self.frame_id += 1
        return sf

    def get_frame_for_llm(self) -> Optional[str]:
        """Returns base64 jpeg of highest motion frame"""
        if not self.ring:
            return None
        best = max(self.ring, key=lambda f: f.motion_score)
        if best.motion_score < 0.01:  # nothing moving
            return None
        _, buf = cv2.imencode('.jpg', best.frame, 
                              [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf).decode()

    def get_frame_by_gps(self, lat, lon, radius_m=10):
        """Get frames near a GPS coordinate"""
        from math import dist
        return [f for f in self.ring 
                if dist((f.gps[0], f.gps[1]), (lat, lon)) < radius_m/111000]
