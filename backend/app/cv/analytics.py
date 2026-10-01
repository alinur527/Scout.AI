"""Legacy EMA/distance/sprint ideas with timestamps and rejected discontinuities."""
import math

import numpy as np


class MatchAnalytics:
    def __init__(self, fps, field_length=105, field_width=68):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("FPS must be positive")
        self.fps, self.field_length, self.field_width = fps, field_length, field_width
        self.player_data, self.player_speeds, self.sprint_count = {}, {}, {}
        self.last_time, self.last_raw, self.last_smoothed = {}, {}, {}
        self.distance, self.sprint_seconds, self.rejected = {}, {}, {}

    def update_metrics(self, track_id, new_coord, timestamp):
        tid = int(track_id)
        point = np.asarray(new_coord, dtype=float)
        if not np.isfinite(point).all():
            return
        if tid not in self.player_data:
            self.player_data[tid], self.player_speeds[tid] = [], []
            self.sprint_count[tid], self.distance[tid], self.sprint_seconds[tid], self.rejected[tid] = 0, 0., 0., 0
        previous_time = self.last_time.get(tid)
        dt = timestamp - previous_time if previous_time is not None else 0
        speed, smoothed = 0., point
        if previous_time is not None:
            if dt <= 0:
                return
            raw_speed = np.linalg.norm(point - self.last_raw[tid]) / dt * 3.6
            if dt > 1.0 or raw_speed > 45:
                self.rejected[tid] += 1
                self.sprint_seconds[tid] = 0
            else:
                alpha = 1 - math.exp(-dt / 0.15)
                smoothed = alpha * point + (1 - alpha) * self.last_smoothed[tid]
                distance = float(np.linalg.norm(smoothed - self.last_smoothed[tid]))
                speed = distance / dt * 3.6
                self.distance[tid] += distance
                if speed > 21:
                    before = self.sprint_seconds[tid]
                    self.sprint_seconds[tid] += dt
                    if before < .6 <= self.sprint_seconds[tid]:
                        self.sprint_count[tid] += 1
                else:
                    self.sprint_seconds[tid] = 0
        self.last_raw[tid], self.last_smoothed[tid], self.last_time[tid] = point, smoothed, timestamp
        self.player_data[tid].append(smoothed.tolist())
        self.player_speeds[tid].append(float(speed))

    def get_total_distance(self, track_id):
        return self.distance.get(int(track_id), 0.)
