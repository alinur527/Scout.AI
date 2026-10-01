import cv2
import numpy as np
import supervision as sv


class AnnotationManager:
    def __init__(self):
        # Используем современные аннотаторы из supervision
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
        self.trace_annotator = sv.TraceAnnotator(thickness=2, trace_length=30)

    def annotate_frame(self, frame, detections, labels):
        """Отрисовка боксов, меток и следов игроков на основном видео."""
        if len(detections) == 0:
            return frame

        annotated_frame = frame.copy()
        annotated_frame = self.box_annotator.annotate(scene=annotated_frame, detections=detections)
        annotated_frame = self.label_annotator.annotate(scene=annotated_frame, detections=detections, labels=labels)
        annotated_frame = self.trace_annotator.annotate(scene=annotated_frame, detections=detections)
        return annotated_frame


class RadarVisualizer:
    def __init__(self, width=300, height=500):
        self.width = width
        self.height = height

    def draw_radar(self, points_meters, player_ids, ball_meters, ball_path, field_dim):
        """Отрисовка тактической карты (радара) с историей мяча."""
        # 1. Создаем фон (зеленое поле)
        radar_img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        radar_img[:] = (34, 139, 34)  # Forest Green

        # 2. Отрисовка разметки (границы и центральная линия)
        cv2.rectangle(radar_img, (0, 0), (self.width, self.height), (255, 255, 255), 2)
        cv2.line(radar_img, (self.width // 2, 0), (self.width // 2, self.height), (255, 255, 255), 1)

        f_len, f_wid = field_dim

        # 3. РИСУЕМ ТРАЕКТОРИЮ МЯЧА (белый след)
        # Добавлена проверка и сглаживание линии (cv2.LINE_AA)
        if ball_path and len(ball_path) > 1:
            for i in range(1, len(ball_path)):
                # Масштабируем и клипируем координаты, чтобы не рисовать за пределами картинки
                x1 = int(np.clip((ball_path[i - 1][0] / f_len) * self.width, 0, self.width))
                y1 = int(np.clip((ball_path[i - 1][1] / f_wid) * self.height, 0, self.height))
                x2 = int(np.clip((ball_path[i][0] / f_len) * self.width, 0, self.width))
                y2 = int(np.clip((ball_path[i][1] / f_wid) * self.height, 0, self.height))

                cv2.line(radar_img, (x1, y1), (x2, y2), (255, 255, 255), 1, cv2.LINE_AA)

        # 4. РИСУЕМ ТЕКУЩИЙ МЯЧ (желтый круг)
        if ball_meters is not None:
            bx = int(np.clip((ball_meters[0] / f_len) * self.width, 0, self.width))
            by = int(np.clip((ball_meters[1] / f_wid) * self.height, 0, self.height))
            # Рисуем контур и заливку для лучшей видимости
            cv2.circle(radar_img, (bx, by), 6, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(radar_img, (bx, by), 7, (0, 0, 0), 1, cv2.LINE_AA)

        # 5. РИСУЕМ ИГРОКОВ (красные точки с ID)
        if len(points_meters) > 0 and player_ids is not None:
            for i, (mx, my) in enumerate(points_meters):
                rx = int(np.clip((mx / f_len) * self.width, 0, self.width))
                ry = int(np.clip((my / f_wid) * self.height, 0, self.height))

                cv2.circle(radar_img, (rx, ry), 5, (0, 0, 255), -1, cv2.LINE_AA)
                cv2.putText(radar_img, str(int(player_ids[i])), (rx + 7, ry),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

        return radar_img
