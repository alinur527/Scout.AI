import cv2
import torch
import numpy as np
from ultralytics import YOLO
import supervision as sv


class VideoProcessor:
    def __init__(self, model_weights="yolo11s-pose.pt"):
        # Авто-выбор девайса: cuda, если есть, иначе cpu
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"🚀 ScoutAI running on: {self.device.upper()}")

        # Загружаем модель и сразу переносим её в память видеокарты
        from ultralytics import YOLO
        self.model = YOLO(model_weights).to(self.device)
        print(f"🚀 Model loaded on {self.device}")
        if self.device == 'cuda':
            self.model()  # Режим FP16 для ускорения

        self.field_polygon = np.array([
            [0, 350], [1280, 350], [1280, 720], [0, 720]
        ], dtype=np.int32)
        # В методе __init__ класса VideoProcessor
        self.tracker = sv.ByteTrack(
            track_activation_threshold=0.35,  # Поднимаем порог, чтобы не плодить "шумные" ID
            lost_track_buffer=90,  # Память 3 секунды (при 30 FPS).
            # Поможет сохранить ID, если игрок отвернулся или скрыт
            minimum_matching_threshold=0.5  # Порог схожести. Снижаем, чтобы легче узнавать игрока
            # в разных позах (сбоку/со спины)
        )

    def process_video(self, source_path):
        # Трекаем людей (0) и мяч (32)
        results_generator = self.model.track(
            source=source_path,
            persist=True,
            classes=[0, 32],  # 0 - люди, 32 - мяч
            conf=0.01,  # ПОНИЖАЕМ ПОРОГ (мяч часто имеет низкий conf)
            iou=0.45,
            imgsz=690,
            half=True,
            device=self.device,
            stream=True
        )

        for result in results_generator:
            frame = result.orig_img

            # 1. Ищем все объекты класса 32 (sports ball)
            ball_boxes = result.boxes[result.boxes.cls == 32]

            ball_pixel = None

            if len(ball_boxes) > 0:
                # Сортируем по уверенности (confidence) и берем лучший
                best_ball = ball_boxes[ball_boxes.conf.argmax()]
                # Вытаскиваем координаты центра xywh
                # Мы берем [0], так как это тензор с одним элементом
                c = best_ball.xywh.cpu().numpy()[0]
                ball_pixel = [float(c[0]), float(c[1])]

                # ДЕБАГ: расскоментируй, чтобы видеть conf мяча в консоли
                # print(f"Ball detected! Conf: {best_ball.conf.item():.2f}")

            # 2. Обработка игроков (Pose + Tracking)
            if getattr(result.boxes, 'id', None) is None:
                yield frame, sv.Detections.empty(), [], ball_pixel
                continue

            detections = sv.Detections.from_ultralytics(result)
            detections = detections[detections.class_id == 0]  # Только люди для трекинга

            # Маскировка (PolygonZone)
            zone = sv.PolygonZone(polygon=self.field_polygon)
            mask = zone.trigger(detections=detections)
            detections = detections[mask]

            # Извлекаем лодыжки (Keypoints 15, 16)
            keypoints = result.keypoints.xy.cpu().numpy()[mask]
            ankle_coords = []
            for person_kp in keypoints:
                l_ankle, r_ankle = person_kp[15], person_kp[16]
                mid_point = (l_ankle + r_ankle) / 2 if np.any(l_ankle) and np.any(r_ankle) else (
                    l_ankle if np.any(l_ankle) else r_ankle)
                ankle_coords.append(mid_point)

            yield frame, detections, ankle_coords, ball_pixel