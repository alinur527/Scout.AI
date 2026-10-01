import numpy as np


# ВАЖНО: Никаких импортов из src.analytics здесь быть не должно!

class MatchAnalytics:
    def __init__(self, fps, field_length=40, field_width=20):
        self.fps = fps
        self.field_length = field_length
        self.field_width = field_width

        # Хранилища данных (ключи всегда приводим к int)
        self.player_data = {}  # Координаты (метры)
        self.player_speeds = {}  # Скорости (км/ч)
        self.player_accels = {}  # Ускорения (м/с^2)
        self.sprint_count = {}  # Счетчик спринтов
        self.possession_time = {}  # Время владения (кадры)

        # Буферы для подавления шума
        self.sprint_buffer = {}  # Кадры непрерывного бега выше порога
        self.last_smoothed = {}  # Предыдущая сглаженная точка
        self.heatmap_data = np.zeros((int(field_length), int(field_width)))

        # --- ПАРАМЕТРЫ ФИЛЬТРАЦИИ (Манеж 5х5) ---
        self.alpha = 0.2  # Коэффициент EMA (0.2 = сильное сглаживание)
        self.sprint_speed = 21.0  # Порог спринта (км/ч)
        self.max_real_speed = 31.0  # Жесткий потолок скорости
        self.sprint_min_duration = int(0.6 * fps)  # Минимум 0.6 сек быстрого бега
        self.ball_dist_threshold = 3.5  # Радиус владения мячом (метры)
        self.ball_buffer = []  # Для сглаживания позиции мяча
        self.ball_path = []  # История передвижения мяча в метрах

    def update_metrics(self, track_id, new_coord, ball_coord=None):
        """Обновляет все метрики игрока на текущем кадре."""
        tid = int(track_id)  # Защита от np.int32

        if tid not in self.player_data:
            self._init_player(tid, new_coord)
            return

        # 1. Сглаживание траектории (EMA)
        # $$S_t = \alpha \cdot X_t + (1 - \alpha) \cdot S_{t-1}$$
        prev_smoothed = self.last_smoothed[tid]
        smoothed_coord = self.alpha * np.array(new_coord) + (1 - self.alpha) * prev_smoothed
        self.last_smoothed[tid] = smoothed_coord

        dist_m = np.linalg.norm(smoothed_coord - prev_smoothed)

        # 2. Расчет скорости (км/ч)
        raw_speed = dist_m * self.fps * 3.6
        speed_kmh = min(raw_speed, self.max_real_speed)

        # 3. Расчет ускорения (м/с²)
        # $$a = \frac{v_t - v_{t-1}}{\Delta t}$$
        prev_speed_ms = self.player_speeds[tid][-1] / 3.6
        curr_speed_ms = speed_kmh / 3.6
        accel = (curr_speed_ms - prev_speed_ms) * self.fps

        # 4. Логика спринтов (защита от ложных срабатываний)
        if speed_kmh > self.sprint_speed:
            self.sprint_buffer[tid] += 1
            if self.sprint_buffer[tid] == self.sprint_min_duration:
                self.sprint_count[tid] += 1
        else:
            self.sprint_buffer[tid] = 0

        # 5. Обновление Тепловой карты
        ix = int(np.clip(smoothed_coord[0], 0, self.field_length - 1))
        iy = int(np.clip(smoothed_coord[1], 0, self.field_width - 1))
        self.heatmap_data[ix, iy] += 1

        # 6. Владение мячом (Проверка дистанции до мяча)
        if ball_coord is not None:
            self.ball_buffer.append(np.array(ball_coord))
            if len(self.ball_buffer) > 5: self.ball_buffer.pop(0)

            # Сглаженная позиция мяча
            smoothed_ball = np.mean(self.ball_buffer, axis=0)

            # Считаем расстояние до игрока (smoothed_coord)
            dist = np.linalg.norm(smoothed_coord - smoothed_ball)

            if dist < self.ball_dist_threshold:  # Тот самый порог 4.0м
                self.possession_time[tid] = self.possession_time.get(tid, 0) + 1

        # Запись истории
        self.player_data[tid].append(smoothed_coord)
        self.player_speeds[tid].append(speed_kmh)
        self.player_accels[tid].append(accel)

    def update_ball(self, ball_coords_meters):
        if ball_coords_meters is not None:
            self.ball_path.append(ball_coords_meters)
            # Храним последние 100 точек для истории
            if len(self.ball_path) > 100:
                self.ball_path.pop(0)

    def _init_player(self, tid, coord):
        """Вспомогательный метод для инициализации нового ID."""
        self.player_data[tid] = [coord]
        self.player_speeds[tid] = [0.0]
        self.player_accels[tid] = [0.0]
        self.sprint_count[tid] = 0
        self.sprint_buffer[tid] = 0
        self.last_smoothed[tid] = np.array(coord)

    def get_total_distance(self, track_id):
        """Возвращает общий пробег игрока в метрах."""
        tid = int(track_id)
        coords = self.player_data.get(tid, [])
        if len(coords) < 10: return 0.0
        diffs = np.diff(np.array(coords), axis=0)
        return float(np.sum(np.linalg.norm(diffs, axis=1)))

    def get_possession_stats(self):
        """Возвращает распределение владения мячом в %."""
        total_p = sum(self.possession_time.values())
        if total_p == 0: return {}
        return {tid: (t / total_p) * 100 for tid, t in self.possession_time.items()}

    def save_to_csv(self, filename="match_report.csv", min_dist_filter=5.0):
        """
        Формирует финальный отчет.
        min_dist_filter: игнорировать игроков, пробежавших меньше X метров.
        """
        import pandas as pd

        report_data = []
        possession_stats = self.get_possession_stats()

        for tid in self.player_data.keys():
            total_dist = self.get_total_distance(tid)

            # Фильтруем "шумные" ID, которые почти не двигались
            if total_dist < min_dist_filter:
                continue

            # Расчет среднего ускорения
            accels = self.player_accels.get(tid, [0.0])
            avg_accel = sum(accels) / len(accels) if accels else 0.0

            # Собираем данные с принудительным приведением типов
            report_data.append({
                "Player_ID": int(tid),
                "Total_Distance_m": float(round(total_dist, 2)),
                "Max_Speed_kmh": float(round(max(self.player_speeds.get(tid, [0.0])), 2)),
                "Avg_Accel_ms2": float(round(avg_accel, 2)),
                "Sprints": int(self.sprint_count.get(tid, 0)),
                "Possession_Pct": float(round(possession_stats.get(tid, 0.0), 2))
            })

        if report_data:
            # Сортируем по дистанции (самые активные сверху)
            df = pd.DataFrame(report_data).sort_values(by="Total_Distance_m", ascending=False)
            df.to_csv(filename, index=False)
            return filename
        return None