"""
Detection Engine: Template Matching (dùng ngay) + YOLOv8 (sau khi train)
"""

import cv2
import numpy as np
from pathlib import Path
from abc import ABC, abstractmethod

PROJECT_DIR = Path(__file__).parent


class BaseDetector(ABC):
    """Base class cho các engine phát hiện nút"""

    @abstractmethod
    def detect(self, screenshot_path: str, label: str) -> tuple[int, int, float] | None:
        """
        Tìm nút có nhãn `label` trong ảnh screenshot.
        Trả về (x, y, confidence) hoặc None nếu không tìm thấy.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Kiểm tra engine có sẵn sàng không"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Tên engine"""
        pass


class TemplateMatchingEngine(BaseDetector):
    """
    Phát hiện nút bằng Template Matching (OpenCV).
    Dùng ảnh crop từ lúc record làm mẫu để tìm trên màn hình.
    """

    def __init__(self):
        self.name = "Template Matching"

    def get_name(self) -> str:
        return self.name

    def is_available(self) -> bool:
        return True  # Luôn có sẵn

    def detect(self, screenshot_path: str, label: str, template_path: str = None) -> tuple[int, int, float] | None:
        """
        Tìm nút trong ảnh screenshot.

        Args:
            screenshot_path: Đường dẫn ảnh chụp màn hình hiện tại
            label: Nhãn nút cần tìm (để tìm template trong templates/)
            template_path: Đường dẫn trực tiếp tới ảnh mẫu (ưu tiên hơn label)

        Returns:
            (x, y, confidence) hoặc None
        """
        # Tìm template
        if template_path:
            template_file = Path(template_path)
        else:
            template_file = PROJECT_DIR / "templates" / f"{label}.png"

        if not template_file.exists():
            return None

        # Đọc ảnh
        screenshot = cv2.imread(screenshot_path)
        template = cv2.imread(str(template_file))

        if screenshot is None or template is None:
            return None

        h_template, w_template = template.shape[:2]
        h_screen, w_screen = screenshot.shape[:2]

        # Template không được lớn hơn ảnh chụp
        if h_template > h_screen or w_template > w_screen:
            return None

        # Multi-scale matching
        best_match = None
        best_confidence = 0

        scales = [0.8, 0.9, 1.0, 1.1, 1.2]

        for scale in scales:
            new_w = int(w_template * scale)
            new_h = int(h_template * scale)

            if new_w > w_screen or new_h > h_screen:
                continue
            if new_w < 10 or new_h < 10:
                continue

            resized = cv2.resize(template, (new_w, new_h))

            result = cv2.matchTemplate(screenshot, resized, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

            if max_val > best_confidence:
                best_confidence = max_val
                center_x = max_loc[0] + new_w // 2
                center_y = max_loc[1] + new_h // 2
                best_match = (center_x, center_y)

        if best_match and best_confidence > 0.6:  # Ngưỡng confidence
            return (best_match[0], best_match[1], best_confidence)

        return None


class YOLOEngine(BaseDetector):
    """
    Phát hiện nút bằng YOLOv8 (đã fine-tune).
    Chỉ hoạt động khi có file best.pt trong models/.
    """

    def __init__(self):
        self.name = "YOLOv8"
        self.model = None
        self._available = False
        self._try_load()

    def _try_load(self):
        """Thử load model YOLO"""
        model_path = PROJECT_DIR / "models" / "best.pt"
        if model_path.exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(str(model_path))
                self._available = True
                print(f"[YOLO] Đã load model từ {model_path}")
            except Exception as e:
                print(f"[YOLO] Lỗi load model: {e}")
                self._available = False

    def get_name(self) -> str:
        if self._available:
            return f"{self.name} (active)"
        return f"{self.name} (chưa có model)"

    def is_available(self) -> bool:
        return self._available

    def detect(self, screenshot_path: str, label: str, template_path: str = None) -> tuple[int, int, float] | None:
        """
        Dùng YOLO để detect nút trong ảnh.

        Args:
            screenshot_path: Đường dẫn ảnh chụp
            label: Nhãn nút cần tìm (class name trong model YOLO)
            template_path: Không dùng cho YOLO

        Returns:
            (x, y, confidence) hoặc None
        """
        if not self._available or self.model is None:
            return None

        results = self.model(screenshot_path, verbose=False)

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                # Lấy class name
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])

                if cls_name == label and conf > 0.5:
                    # Lấy tọa độ tâm
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    return (center_x, center_y, conf)

        return None

    def detect_all(self, screenshot_path: str) -> list[dict]:
        """
        Detect tất cả nút trong ảnh.
        Trả về list các dict: {label, x, y, confidence, bbox}
        """
        if not self._available or self.model is None:
            return []

        results = self.model(screenshot_path, verbose=False)
        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = result.names[cls_id]
                conf = float(box.conf[0])

                if conf > 0.5:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    detections.append({
                        "label": cls_name,
                        "x": center_x,
                        "y": center_y,
                        "confidence": conf,
                        "bbox": (int(x1), int(y1), int(x2), int(y2)),
                    })

        return detections


class HybridDetector:
    """
    Detector kết hợp: dùng YOLO nếu có, fallback sang Template Matching.
    """

    def __init__(self):
        self.yolo = YOLOEngine()
        self.template = TemplateMatchingEngine()

        # Chọn engine chính
        if self.yolo.is_available():
            self.primary = self.yolo
            self.fallback = self.template
        else:
            self.primary = self.template
            self.fallback = None

    def detect(self, screenshot_path: str, label: str, template_path: str = None) -> tuple[int, int, float, str] | None:
        """
        Tìm nút, thử engine chính trước rồi fallback.
        Trả về (x, y, confidence, engine_name) hoặc None.
        """
        # Thử engine chính
        result = self.primary.detect(screenshot_path, label, template_path)
        if result:
            return (*result, self.primary.get_name())

        # Fallback
        if self.fallback:
            result = self.fallback.detect(screenshot_path, label, template_path)
            if result:
                return (*result, self.fallback.get_name())

        return None

    def get_status(self) -> str:
        """Trạng thái detector"""
        if self.yolo.is_available():
            return f"YOLOv8 active | Fallback: Template Matching"
        return "Template Matching (YOLO chưa sẵn sàng)"
