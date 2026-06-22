"""
Record mode: Ghi lại thao tác trên điện thoại
- Bắt sự kiện chạm qua adb getevent
- Hiện popup dán nhãn
- Lưu macro + dataset
"""

import time
import threading
import os
from pathlib import Path
from datetime import datetime
from PIL import Image

from adb_utils import screenshot, get_screen_size, get_touch_device
from macro_manager import save_macro, save_to_dataset

PROJECT_DIR = Path(__file__).parent


class Recorder:
    """Ghi macro từ thao tác trên điện thoại"""

    def __init__(self, chat_ui, detector=None):
        self.chat_ui = chat_ui
        self.detector = detector

        self.recording = False
        self.record_start_time = 0
        self.paused_time = 0.0
        self.pause_start = 0

        self.steps: list[dict] = []
        self.record_name = ""

        self._monitor_thread = None
        self._stop_monitor = False

        self.screen_w = 720
        self.screen_h = 1280
        self.touch_w = 0
        self.touch_h = 0
        self._scale_x = 1.0
        self._scale_y = 1.0

        os.makedirs(PROJECT_DIR / "screenshots", exist_ok=True)
        os.makedirs(PROJECT_DIR / "templates", exist_ok=True)

    def start(self, name: str = None):
        if not name:
            name = datetime.now().strftime("macro_%Y%m%d_%H%M%S")
        self.record_name = name
        self.steps = []
        self.recording = True
        self.record_start_time = time.time()
        self.paused_time = 0.0
        self.pause_start = 0
        self._stop_monitor = False
        self.screen_w, self.screen_h = get_screen_size()
        self.touch_w, self.touch_h = self._get_touch_size()
        self._scale_x = self.screen_w / self.touch_w if self.touch_w > 0 else 1.0
        self._scale_y = self.screen_h / self.touch_h if self.touch_h > 0 else 1.0
        self.chat_ui.bot_say(f"📹 Bắt đầu ghi: {name}")
        self.chat_ui.bot_info(f"Màn hình: {self.screen_w}x{self.screen_h}")
        if self._scale_x != 1.0 or self._scale_y != 1.0:
            self.chat_ui.bot_info(f"Touch panel: {self.touch_w}x{self.touch_h} -> scale ({self._scale_x:.2f}, {self._scale_y:.2f})")
        self.chat_ui.bot_info("Hay dung dien thoai tu nhien. Go 'stop' de dung.")
        self.chat_ui.update_status(f"DANG GHI: {name}")
        self._monitor_thread = threading.Thread(target=self._monitor_touches, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self._stop_monitor = True
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2)
        self.chat_ui.set_recording_state(False)
        elapsed = time.time() - self.record_start_time - self.paused_time
        if self.steps:
            filepath = save_macro(self.record_name, self.steps)
            self.chat_ui.bot_success(f"Da luu macro: {self.record_name} ({len(self.steps)} buoc, {elapsed:.1f}s thuc)")
            labels = {}
            for step in self.steps:
                lbl = step.get("label", "?")
                labels[lbl] = labels.get(lbl, 0) + 1
            stats = " | ".join([f"{k}: {v}" for k, v in labels.items()])
            self.chat_ui.bot_info(f"Thong ke: {stats}")
            self.chat_ui.bot_info(f"Macro: {filepath}")
        else:
            self.chat_ui.bot_say("Chua co thao tac nao duoc ghi")
        self.chat_ui.update_status("San sang")

    def _get_elapsed(self) -> float:
        if self.pause_start > 0:
            current_pause = time.time() - self.pause_start
        else:
            current_pause = 0
        return time.time() - self.record_start_time - self.paused_time - current_pause

    def _pause_timer(self):
        self.pause_start = time.time()

    def _resume_timer(self):
        if self.pause_start > 0:
            self.paused_time += time.time() - self.pause_start
            self.pause_start = 0

    def _monitor_touches(self):
        import traceback
        import subprocess
        import time as _time
        try:
            device = get_touch_device()
            adbl = str(PROJECT_DIR / "scrcpy" / "adb.exe")
            batch_num = 0
            while not self._stop_monitor and self.recording:
                batch_num += 1
                cmd = [adbl, "shell", f"getevent -c 20 {device}"]
                print(f"[RECORD] Batch #{batch_num}...")
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                except subprocess.TimeoutExpired:
                    print(f"[RECORD] Batch #{batch_num}: timeout")
                    continue
                except Exception as ex:
                    print(f"[RECORD] Batch #{batch_num}: {ex}")
                    continue
                if self._stop_monitor or not self.recording:
                    break
                output = result.stdout.strip()
                lines = output.split("\n")
                if not output:
                    continue
                current_x = 0
                current_y = 0
                is_down = False
                touch_detected = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 3:
                        continue
                    ev_type = parts[0]
                    ev_code = parts[1]
                    ev_value = parts[2]
                    if ev_type == "0003" and ev_code == "0035":
                        current_x = int(ev_value, 16)
                    elif ev_type == "0003" and ev_code == "0036":
                        current_y = int(ev_value, 16)
                    elif ev_type == "0003" and ev_code == "0039":
                        val = int(ev_value, 16)
                        if val == 0xFFFFFFFF:
                            is_down = False
                        elif not is_down:
                            is_down = True
                    elif ev_type == "0001" and ev_code == "014a":
                        is_down = (ev_value == "00000001")
                    elif ev_type == "0000" and ev_code == "0000":
                        if is_down and current_x > 0 and current_y > 0:
                            screen_x = int(current_x * self._scale_x)
                            screen_y = int(current_y * self._scale_y)
                            self._handle_touch(screen_x, screen_y)
                            touch_detected = True
                            is_down = False
                if touch_detected:
                    print(f"[RECORD] Batch #{batch_num}: touch detected")
                elif len(lines) < 5:
                    _time.sleep(0.05)
        except Exception as e:
            if self.recording:
                self.chat_ui.bot_error(f"Loi monitor: {e}")
                traceback.print_exc()

    def _get_touch_size(self) -> tuple[int, int]:
        from adb_utils import _adb
        device = get_touch_device()
        if not device:
            return (0, 0)
        try:
            output = _adb(f"shell getevent -p {device}")
            max_x, max_y = 0, 0
            for line in output.split("\n"):
                if "0035" in line and "max" in line:
                    for p in line.split(","):
                        if "max" in p:
                            max_x = int(p.strip().split()[-1])
                if "0036" in line and "max" in line:
                    for p in line.split(","):
                        if "max" in p:
                            max_y = int(p.strip().split()[-1])
            return (max_x, max_y)
        except:
            return (0, 0)

    def _handle_touch(self, screen_x: int, screen_y: int):
        if not self.recording:
            return
        print(f"[RECORD] Touch at ({screen_x},{screen_y})")
        self._pause_timer()
        timestamp = self._get_elapsed()
        screen_path = screenshot()
        crop_path = self._crop_around(screen_path, screen_x, screen_y)

        def on_label(label: str | None):
            if label == "__STOP__":
                self._resume_timer()
                self.stop()
                return
            if label:
                step = {
                    "timestamp": round(timestamp, 2),
                    "type": "tap",
                    "label": label,
                    "x": screen_x,
                    "y": screen_y,
                    "screen_w": self.screen_w,
                    "screen_h": self.screen_h,
                    "image_crop": crop_path,
                }
                self.steps.append(step)
                self._save_template(crop_path, label)
                try:
                    save_to_dataset(label, crop_path, screen_x, screen_y, self.screen_w, self.screen_h)
                except Exception:
                    pass
                self.chat_ui.bot_success(f'Da luu: "{label}" tai ({screen_x}, {screen_y}) [{timestamp:.1f}s]')
            else:
                self.chat_ui.bot_say(f"Da bo qua cham tai ({screen_x}, {screen_y})")
            self._resume_timer()
        self.chat_ui.request_popup("Dan nhan", f"Ban vua cham ({screen_x}, {screen_y}) - day la nut gi?", on_label)

    def _crop_around(self, image_path: str, center_x: int, center_y: int, crop_size: int = 200) -> str:
        try:
            img = Image.open(image_path)
            img_w, img_h = img.size
            half = crop_size // 2
            left = max(0, center_x - half)
            top = max(0, center_y - half)
            right = min(img_w, center_x + half)
            bottom = min(img_h, center_y + half)
            if right <= left or bottom <= top:
                return image_path
            cropped = img.crop((left, top, right, bottom))
            crop_dir = PROJECT_DIR / "screenshots" / "crops"
            os.makedirs(crop_dir, exist_ok=True)
            crop_path = crop_dir / f"crop_{int(time.time()*1000)}.png"
            cropped.save(str(crop_path))
            return str(crop_path)
        except Exception as e:
            print(f"[CROP] {e}")
            return image_path

    def _save_template(self, crop_path: str, label: str):
        templates_dir = PROJECT_DIR / "templates"
        os.makedirs(templates_dir, exist_ok=True)
        dst = templates_dir / f"{label}.png"
        try:
            img = Image.open(crop_path)
            img.save(str(dst))
        except Exception:
            pass

    def add_text_step(self, text: str):
        if not self.recording:
            self.chat_ui.bot_error("Chua bat dau record!")
            return
        timestamp = self._get_elapsed()
        step = {
            "timestamp": round(timestamp, 2),
            "type": "text",
            "label": "text",
            "x": 0, "y": 0,
            "text_content": text,
        }
        self.steps.append(step)
        self.chat_ui.bot_success(f'Da luu text: "{text}" [{timestamp:.1f}s]')

    def add_swipe_step(self, direction: str = "up"):
        if not self.recording:
            self.chat_ui.bot_error("Chua bat dau record!")
            return
        timestamp = self._get_elapsed()
        step = {
            "timestamp": round(timestamp, 2),
            "type": "swipe",
            "label": f"swipe_{direction}",
            "direction": direction,
        }
        self.steps.append(step)
        self.chat_ui.bot_success(f"Da luu swipe: {direction} [{timestamp:.1f}s]")
