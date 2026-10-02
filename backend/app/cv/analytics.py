"""Legacy EMA/distance/sprint ideas with timestamps and rejected discontinuities."""

import math

import numpy as np


class MatchAnalytics:
    def __init__(self, fps, field_length=105, field_width=68, smoothing_seconds=0.15):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("FPS must be positive")
        self.fps, self.field_length, self.field_width = fps, field_length, field_width
        self.player_data, self.player_speeds, self.sprint_count = {}, {}, {}
        self.last_time, self.last_raw, self.last_smoothed = {}, {}, {}
        self.distance, self.sprint_seconds, self.rejected = {}, {}, {}
        if not math.isfinite(smoothing_seconds) or smoothing_seconds < 0:
            raise ValueError("Smoothing duration must be finite and nonnegative")
        self.smoothing_seconds = smoothing_seconds
        self.segments, self.invalid_coordinates, self.pending_break = {}, {}, set()
        self.max_gap_seconds = 0.5

    def update_metrics(self, track_id, new_coord, timestamp):
        tid = int(track_id)
        try:
            point = np.asarray(new_coord, dtype=float)
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            self.invalid_coordinates[tid] = self.invalid_coordinates.get(tid, 0) + 1
            self.pending_break.add(tid)
            return
        if point.shape != (2,) or not np.isfinite(point).all() or not math.isfinite(timestamp):
            self.invalid_coordinates[tid] = self.invalid_coordinates.get(tid, 0) + 1
            self.pending_break.add(tid)
            return
        if tid not in self.player_data:
            self.player_data[tid], self.player_speeds[tid] = [], []
            self.sprint_count[tid], self.distance[tid], self.sprint_seconds[tid], self.rejected[tid] = (
                0,
                0.0,
                0.0,
                0,
            )
            self.segments[tid] = [[]]
        previous_time = self.last_time.get(tid)
        dt = timestamp - previous_time if previous_time is not None else 0
        speed, smoothed = 0.0, point
        if previous_time is not None:
            if dt <= 0:
                return
            raw_speed = np.linalg.norm(point - self.last_raw[tid]) / dt * 3.6
            if dt > self.max_gap_seconds or raw_speed > 45 or tid in self.pending_break:
                self.rejected[tid] += 1
                self.sprint_seconds[tid] = 0
                self.segments[tid].append([])
            else:
                alpha = 1 - math.exp(-dt / self.smoothing_seconds) if self.smoothing_seconds else 1
                smoothed = alpha * point + (1 - alpha) * self.last_smoothed[tid]
                distance = float(np.linalg.norm(smoothed - self.last_smoothed[tid]))
                speed = distance / dt * 3.6
                self.distance[tid] += distance
                if speed > 21:
                    before = self.sprint_seconds[tid]
                    self.sprint_seconds[tid] += dt
                    if before < 0.6 <= self.sprint_seconds[tid]:
                        self.sprint_count[tid] += 1
                else:
                    self.sprint_seconds[tid] = 0
        self.last_raw[tid], self.last_smoothed[tid], self.last_time[tid] = point, smoothed, timestamp
        self.player_data[tid].append(smoothed.tolist())
        self.segments[tid][-1].append(smoothed.tolist())
        self.player_speeds[tid].append(float(speed))
        self.pending_break.discard(tid)

    def get_total_distance(self, track_id):
        return self.distance.get(int(track_id), 0.0)
