import cv2
import numpy as np


class FieldTransformer:
    def __init__(self, source_points=None, field_length=None, field_width=None, custom_matrix=None):
        """
        source_points: 4 точки на видео [[x,y], ...]
        field_length, field_width: размеры поля в метрах
        custom_matrix: готовая матрица (если используется авто-калибровка)
        """
        if custom_matrix is not None:
            self.M = custom_matrix
        else:
            # Ручная калибровка по 4 точкам
            # Мы сопоставляем их с углами прямоугольника в метрах
            self.dest_points = np.array([
                [0, 0],
                [field_length, 0],
                [field_length, field_width],
                [0, field_width]
            ], dtype="float32")

            self.source_points = np.array(source_points, dtype="float32")
            self.M = cv2.getPerspectiveTransform(self.source_points, self.dest_points)

    def transform_points(self, points):
        """Преобразует пиксели в метры через матрицу гомографии."""
        if len(points) == 0:
            return points

        # Подготовка точек для cv2.perspectiveTransform
        points = np.array(points).reshape(-1, 1, 2).astype("float32")
        transformed = cv2.perspectiveTransform(points, self.M)
        return transformed.reshape(-1, 2)


class GeometryCalibrator:
    def __init__(self):
        self.M = None

    def compute_homography_simple(self, frame, field_l, field_w):
        """
        Автоматически ищет линии разметки и строит матрицу.
        Для видео 'с уровня глаз' мы ищем пересечение центральной и боковой линий.
        """
        # 1. Цветовая маска для белых линий
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 180])  # Порог белого
        upper_white = np.array([180, 60, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # 2. Морфологическая очистка (убираем шум)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # 3. Поиск линий (Hough Lines)
        edges = cv2.Canny(mask, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=100, maxLineGap=20)

        if lines is None:
            return np.eye(3)  # Возвращаем единичную матрицу при неудаче

        # Разделяем на горизонтальные и вертикальные
        h_lines = []
        v_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            if angle < 25 or angle > 155:
                h_lines.append(line[0])
            elif 65 < angle < 115:
                v_lines.append(line[0])

        if not h_lines or not v_lines:
            return np.eye(3)

        # Берем самые длинные линии как основные оси
        h_main = max(h_lines, key=lambda l: np.linalg.norm([l[0] - l[2], l[1] - l[3]]))
        v_main = max(v_lines, key=lambda l: np.linalg.norm([l[0] - l[2], l[1] - l[3]]))

        # Находим точку пересечения (Anchor)
        anchor_px = self._get_intersection(h_main, v_main)

        # Генерируем виртуальные 4 точки для гомографии на основе этого пересечения
        # Мы предполагаем, что это центр боковой линии (FieldLength/2, 0)
        src_pts = np.array([
            anchor_px,
            [anchor_px[0] + 150, anchor_px[1]],  # точка дальше по боковой
            [v_main[0], v_main[1]],  # точка вглубь поля
            [anchor_px[0] + 150, v_main[1]]
        ], dtype="float32")

        dst_pts = np.array([
            [field_l / 2, 0],
            [field_l / 2 + 10, 0],
            [field_l / 2, 10],
            [field_l / 2 + 10, 10]
        ], dtype="float32")

        return cv2.getPerspectiveTransform(src_pts, dst_pts)

    def _get_intersection(self, l1, l2):
        x1, y1, x2, y2 = l1
        x3, y3, x4, y4 = l2
        denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / (denom + 1e-6)
        return [int(x1 + ua * (x2 - x1)), int(y1 + ua * (y2 - y1))]