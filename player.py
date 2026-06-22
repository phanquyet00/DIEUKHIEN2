"""
Replay mode: Phát lại macro đã ghi
"""

import time
import threading
from adb_utils import screenshot, tap, swipe, input_text, get_screen_size
from detector import HybridDetector


class Player:
    """Phát lại macro"""

    def __init__(self, chat_ui):
        self.chat_ui = chat_ui
        self.detector = HybridDetector()
        self.playing = False
        self._stop_play = False
        self._play_thread = None

    def play(self, macro_name: str):
        """Phát lại macro"""
        from macro_manager import load_macro

        macro = load_macro(macro_name)
        if not macro:
            self.chat_ui.bot_error(f"Không tìm thấy macro: {macro_name}")
            self.chat_ui.bot_info(
                f"Các macro hiện có: {self._list_macros_str()}"
            )
            return

        if self.playing:
            self.chat_ui.bot_error("Đang phát macro khác. Gõ 'stop' để dừng.")
            return

        steps = macro.get("steps", [])
        if not steps:
            self.chat_ui.bot_error("Macro trống!")
            return

        self.playing = True
        self._stop_play = False

        self.chat_ui.bot_say(f"▶️ Phát macro: {macro_name} ({len(steps)} bước)")
        self.chat_ui.bot_info(f"Engine: {self.detector.get_status()}")
        self.chat_ui.update_status(f"🟡 ĐANG PHÁT: {macro_name}")

        def _run_and_finish():
            self._run_macro(steps, loop_index=0)
            self.playing = False
            self.chat_ui.set_playing_state(False)
            self.chat_ui.bot_success(
                f"🎉 Xong macro! {len(steps)} bước"
            )
            self.chat_ui.update_status("🟢 Sẵn sàng")

        self._play_thread = threading.Thread(target=_run_and_finish, daemon=True)
        self._play_thread.start()

    def play_sequence(self, macro_names: list[str]):
        """Chạy tuần tự nhiều macro"""
        from macro_manager import load_macro

        if self.playing:
            self.chat_ui.bot_error("Đang phát macro khác. Gõ 'stop' để dừng.")
            return

        self.playing = True
        self._stop_play = False

        self.chat_ui.update_status(f"🟡 ĐANG PHÁT TUẦN TỰ: {len(macro_names)} macro")

        def _run_sequence():
            for idx, mname in enumerate(macro_names):
                if self._stop_play:
                    break

                macro = load_macro(mname)
                if not macro:
                    self.chat_ui.bot_error(f"Không tìm thấy: {mname}")
                    continue

                steps = macro.get("steps", [])
                if not steps:
                    continue

                self.chat_ui.bot_say(f"▶️ [{idx+1}/{len(macro_names)}] {mname} ({len(steps)} bước)")
                self._run_macro(steps, loop_index=0)
                self.chat_ui.bot_success(f"✅ [{idx+1}/{len(macro_names)}] Xong {mname}")

            self.playing = False
            self.chat_ui.set_playing_state(False)
            self.chat_ui.bot_success("🎉 Xong tất cả macro!")
            self.chat_ui.update_status("🟢 Sẵn sàng")

        self._play_thread = threading.Thread(target=_run_sequence, daemon=True)
        self._play_thread.start()

    def play_lap_forever(self, macro_name: str):
        """Chay lap vo han den khi bam Dung"""
        from macro_manager import load_macro
        if self.playing:
            self.chat_ui.bot_error("Dang phat macro khac. Go 'stop' de dung.")
            return
        macro = load_macro(macro_name)
        if not macro:
            self.chat_ui.bot_error(f"Khong tim thay macro: {macro_name}")
            return
        steps = macro.get("steps", [])
        if not steps:
            self.chat_ui.bot_error("Macro trong!")
            return
        self.playing = True
        self._stop_play = False
        self.chat_ui.update_status(f"LAP VO HAN: {macro_name}")
        def _run():
            count = 0
            while not self._stop_play:
                count += 1
                self.chat_ui.bot_info(f"Lap #{count}...")
                self._run_macro(steps, loop_index=count - 1)
            self.playing = False
            self.chat_ui.set_playing_state(False)
            self.chat_ui.bot_info(f"Da dung sau {count} vong lap")
            self.chat_ui.update_status("San sang")
        self._play_thread = threading.Thread(target=_run, daemon=True)
        self._play_thread.start()

    def play_loop(self, macro_name: str):
        """Chạy lặp macro liên tục đến khi bấm dừng"""
        from macro_manager import load_macro

        if self.playing:
            self.chat_ui.bot_error("Đang phát macro khác. Gõ 'stop' để dừng.")
            return

        macro = load_macro(macro_name)
        if not macro:
            self.chat_ui.bot_error(f"Không tìm thấy macro: {macro_name}")
            return

        steps = macro.get("steps", [])
        if not steps:
            self.chat_ui.bot_error("Macro trống!")
            return

        self.playing = True
        self._stop_play = False
        self.chat_ui.update_status(f"🔁 ĐANG LẶP: {macro_name}")

        def _run_loop():
            # Đếm số tọa độ tối đa (từ bước có nhiều coords nhất)
            max_coords = 0
            for s in steps:
                coords = s.get("coords", [[s.get("x", 0), s.get("y", 0)]])
                max_coords = max(max_coords, len(coords))

            for loop_idx in range(max_coords):
                if self._stop_play:
                    break
                if max_coords > 1:
                    self.chat_ui.bot_info(f"▶️ Lần chạy {loop_idx+1}/{max_coords}...")
                self._run_macro(steps, loop_index=loop_idx)

            self.playing = False
            self.chat_ui.set_playing_state(False)
            if max_coords > 1:
                self.chat_ui.bot_success(f"🎉 Xong! Đã chạy {max_coords} lần")
            else:
                self.chat_ui.bot_success("🎉 Xong macro!")

        self._play_thread = threading.Thread(target=_run_loop, daemon=True)
        self._play_thread.start()

    def stop(self):
        """Dừng phát"""
        if not self.playing:
            return
        self._stop_play = True
        self.playing = False
        self.chat_ui.set_playing_state(False)
        self.chat_ui.bot_say("⏹️ Đã dừng phát macro")
        self.chat_ui.update_status("🟢 Sẵn sàng")

    def _run_macro(self, steps: list[dict], loop_index: int = 0):
        """Chạy từng bước trong macro. loop_index = số vòng lặp hiện tại (cho tọa độ phụ)"""
        screen_w, screen_h = get_screen_size()
        total = len(steps)
        success_count = 0

        for i, step in enumerate(steps):
            if self._stop_play:
                break

            timestamp = step.get("timestamp", 0)
            step_type = step.get("type", "tap")
            label = step.get("label", "?")
            progress = f"[{i+1}/{total}]"

            # Tính thời gian chờ từ bước trước
            if i > 0:
                prev_timestamp = steps[i - 1].get("timestamp", 0)
                wait_time = timestamp - prev_timestamp
                if wait_time > 0:
                    self.chat_ui.bot_info(f"⏳ Đợi {wait_time:.1f}s...")
                    self._sleep_interruptible(wait_time)

            if self._stop_play:
                break

            try:
                if step_type == "tap":
                    self._execute_tap(step, progress, screen_w, screen_h, loop_index)
                    success_count += 1

                elif step_type == "swipe":
                    self._execute_swipe(step, progress, screen_w, screen_h)
                    success_count += 1

                elif step_type == "text":
                    self._execute_text(step, progress)
                    success_count += 1

                else:
                    self.chat_ui.bot_error(f"{progress} Loại không hỗ trợ: {step_type}")

            except Exception as e:
                self.chat_ui.bot_error(f"{progress} Lỗi: {e}")

        if loop_index == 0:
            # Chỉ hiện thông báo xong khi không phải loop
            pass
        self.chat_ui.update_status("🟢 Sẵn sàng")

    def _execute_tap(self, step: dict, progress: str, screen_w: int, screen_h: int,
                      loop_index: int = 0):
        """Thực hiện bước tap, hỗ trợ nhiều tọa độ cho lặp"""
        label = step.get("label", "?")

        # Lấy tọa độ cho vòng lặp hiện tại
        coords = step.get("coords", [[step.get("x", 0), step.get("y", 0)]])
        coord_idx = loop_index % len(coords)
        coord_data = coords[coord_idx]
        orig_x, orig_y = coord_data[0], coord_data[1]
        coord_name = coord_data[2] if len(coord_data) > 2 else ""

        if len(coords) > 1:
            name_str = f" \"{coord_name}\"" if coord_name else ""
            progress += f" [tọa độ {coord_idx+1}/{len(coords)}{name_str}]"

        template_path = step.get("image_crop", None)

        # Chụp màn hình hiện tại
        screen_path = screenshot()

        # Tìm nút
        result = self.detector.detect(screen_path, label, template_path)

        if result:
            x, y, confidence, engine = result
            tap(x, y)
            self.chat_ui.bot_success(
                f"{progress} Click \"{label}\" tại ({x}, {y}) "
                f"[{engine}, {confidence:.0%}]"
            )
        else:
            # Fallback: dùng tọa độ gốc (đã scale)
            # Scale tọa độ nếu màn hình khác kích thước
            orig_screen_w = step.get("screen_w", screen_w)
            orig_screen_h = step.get("screen_h", screen_h)
            scale_x = screen_w / orig_screen_w
            scale_y = screen_h / orig_screen_h
            fallback_x = int(orig_x * scale_x)
            fallback_y = int(orig_y * scale_y)

            tap(fallback_x, fallback_y)
            self.chat_ui.bot_say(
                f"{progress} Click \"{label}\" tại ({fallback_x}, {fallback_y}) "
                f"[fallback tọa độ gốc]"
            )

    def _execute_swipe(self, step: dict, progress: str, screen_w: int, screen_h: int):
        """Thuc hien vuot - ho tro do dai"""
        direction = step.get("direction", "up")
        try:
            pct = int(step.get("length", "5")) * 5
        except ValueError:
            pct = 25
        pct = max(5, min(50, pct))
        dist = int(pct * screen_h / 100)
        cx = step.get("x", screen_w // 2)
        cy = step.get("y", screen_h // 2)
        if direction == "up":
            x1, y1 = cx, cy
            x2, y2 = cx, cy - dist
        elif direction == "down":
            x1, y1 = cx, cy
            x2, y2 = cx, cy + dist
        elif direction == "left":
            x1, y1 = cx, cy
            x2, y2 = cx - dist, cy
        elif direction == "right":
            x1, y1 = cx, cy
            x2, y2 = cx + dist, cy
        else:
            x1, y1 = cx, cy
            x2, y2 = cx, cy - dist
        x2 = max(0, min(screen_w, x2))
        y2 = max(0, min(screen_h, y2))
        from adb_utils import swipe as adb_swipe
        adb_swipe(x1, y1, x2, y2, 300)
        self.chat_ui.bot_success(f"{progress} Vuot {direction} ({length_key})")

    def _execute_text(self, step: dict, progress: str):
        """Go text len dien thoai"""
        from adb_utils import _adb
        text = step.get("text_content", "")
        clear_first = step.get("clear_first", False)
        if clear_first:
            for _ in range(30):
                _adb("shell input keyevent 67")
        if text:
            import subprocess
            from pathlib import Path
            import time
            try:
                adb = str(Path(__file__).parent / "scrcpy" / "adb.exe")
                time.sleep(0.2)
                for ch in text:
                    if ch == ' ':
                        subprocess.run([adb, "shell", "input", "keyevent", "62"], capture_output=True, timeout=5)
                    else:
                        subprocess.run([adb, "shell", "input", "text", ch], capture_output=True, timeout=5)
                    time.sleep(0.05)
            except Exception as ex:
                print(f"Text error: {ex}")
                self.chat_ui.bot_success(f"{progress} Go text")
    def _sleep_interruptible(self, seconds: float):
        """Ngủ có thể bị ngắt"""
        interval = 0.1
        elapsed = 0
        while elapsed < seconds and not self._stop_play:
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval

    def _list_macros_str(self) -> str:
        """Liệt kê macro dạng string"""
        from macro_manager import list_macros
        macros = list_macros()
        return ", ".join(macros) if macros else "(chưa có macro nào)"

    def list_macros(self):
        """Hiện danh sách macro"""
        from macro_manager import list_macros
        macros = list_macros()
        if macros:
            self.chat_ui.bot_info(f"Macro đã lưu: {', '.join(macros)}")
        else:
            self.chat_ui.bot_say("Chưa có macro nào. Gõ 'record' để tạo.")
