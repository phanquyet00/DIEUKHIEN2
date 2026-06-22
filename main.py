"""
TikTok Auto Bot - Main Entry Point
Kết nối tất cả module: Chat UI + ADB + Record/Replay + Detector
"""

import os
import sys
from pathlib import Path

# Fix encoding cho Windows (hỗ trợ tiếng Việt)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Thêm project root vào path
PROJECT_DIR = Path(__file__).parent
os.chdir(PROJECT_DIR)

# Tạo các thư mục cần thiết
for d in ["screenshots", "screenshots/crops", "templates", "macros", "dataset", "models"]:
    os.makedirs(PROJECT_DIR / d, exist_ok=True)

from chat_ui import ChatUI
from recorder import Recorder
from player import Player
from detector import HybridDetector
from adb_utils import check_device, screenshot, tap, swipe, input_text, get_screen_size


class TikTokBot:
    """Kết nối tất cả module lại với nhau"""

    def __init__(self):
        self.ui = ChatUI("🤖 TikTok Auto Bot")
        self.recorder = Recorder(self.ui)
        self.player = Player(self.ui)
        self.detector = HybridDetector()

        # Đặt callback xử lý lệnh
        self.ui.set_command_callback(self._handle_command)

        # Kiểm tra thiết bị khi khởi động
        self._check_on_startup()

    def _check_on_startup(self):
        """Kiểm tra kết nối khi khởi động"""
        device = check_device()
        if device:
            screen_w, screen_h = get_screen_size()
            self.ui.bot_say(f"🤖 TikTok Auto Bot sẵn sàng!")
            self.ui.bot_info(f"Thiết bị: {device}")
            self.ui.bot_info(f"Màn hình: {screen_w}x{screen_h}")
            self.ui.bot_info(f"Engine: {self.detector.get_status()}")
            self.ui.bot_info("Gõ 'help' để xem danh sách lệnh")
            self.ui.bot_info("Gõ 'record' để bắt đầu ghi macro")
            self.ui.update_status(f"🟢 Sẵn sàng | {self.detector.get_status()}")
        else:
            self.ui.bot_error("Không tìm thấy thiết bị!")
            self.ui.bot_info("Hãy cắm USB và bật USB Debugging trên điện thoại")
            self.ui.bot_info("Sau đó gõ 'check' để kiểm tra lại")
            self.ui.update_status("🔴 Chưa kết nối")

    def _handle_command(self, text: str):
        """Xử lý lệnh từ chat"""
        text = text.strip().lower()
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # === Lệnh hệ thống ===
        if cmd == "help":
            self._cmd_help()

        elif cmd == "check":
            self._cmd_check()

        elif cmd == "screen":
            self._cmd_screen()

        elif cmd == "status":
            self._cmd_status()

        # === Lệnh record ===
        elif cmd == "record":
            self._cmd_record(args)

        elif cmd == "text" and self.recorder.recording:
            self.recorder.add_text_step(args)

        elif cmd == "swipe" and self.recorder.recording:
            self.recorder.add_swipe_step(args or "up")

        elif cmd == "stop":
            self._cmd_stop()

        # === Lệnh replay ===
        elif cmd == "play":
            self._cmd_play(args)

        elif cmd == "macros":
            self.player.list_macros()

        elif cmd == "loop":
            self._cmd_loop(args)

        elif cmd == "lap_forever":
            self._cmd_lap_forever(args)

        elif cmd == "seq":
            self._cmd_seq(args)

        elif cmd == "delete":
            self._cmd_delete(args)

        elif cmd == "clear_dataset":
            self._cmd_clear_dataset(args)

        # === Lệnh live ===
        elif cmd == "like":
            self._cmd_live_tap("like", args)

        elif cmd == "follow":
            self._cmd_live_tap("follow", args)

        elif cmd == "comment":
            self._cmd_comment(args)

        elif cmd == "scroll":
            self._cmd_scroll()

        elif cmd == "capture":
            self._cmd_capture(args)

        elif cmd == "tap":
            self._cmd_tap(args)

        # === Lệnh YOLO ===
        elif cmd == "yolo":
            self._cmd_yolo(args)

        elif cmd == "dataset":
            self._cmd_dataset()

        else:
            if self.recorder.recording:
                self.ui.bot_error(f"Lệnh không hợp lệ: {cmd}")
                self.ui.bot_info("Các lệnh khi record: text <nội dung>, swipe <hướng>, stop")
            else:
                self.ui.bot_error(f"Không hiểu lệnh: {cmd}. Gõ 'help' để xem danh sách.")

    # ============================================================
    # LỆNH HỆ THỐNG
    # ============================================================

    def _cmd_help(self):
        self.ui.bot_say("""
📋 DANH SÁCH LỆNH:

🔧 Hệ thống:
  help              - Hiện trợ giúp
  check             - Kiểm tra kết nối điện thoại
  screen            - Chụp màn hình test
  status            - Xem trạng thái

🎬 Record (ghi macro):
  record [tên]      - Bắt đầu ghi
  text <nội dung>   - Ghi bước gõ text
  swipe [hướng]     - Ghi bước vuốt (up/down/left/right)
  stop              - Dừng ghi & lưu macro

▶️ Replay (phát macro):
  play <tên>        - Phát macro đã lưu
  macros            - Xem danh sách macro
  delete <tên>      - Xóa macro
  clear_dataset [class] - Xóa dataset (1 class hoặc tất cả)

🎮 Live (điều khiển trực tiếp):
  like [N]          - Like video (N lần)
  follow            - Follow
  comment <text>    - Comment
  scroll            - Lướt video tiếp

🤖 YOLO:
  yolo              - Kiểm tra trạng thái YOLO
  dataset           - Xem thống kê dataset
""".strip())

    def _cmd_check(self):
        device = check_device()
        if device:
            w, h = get_screen_size()
            self.ui.bot_success(f"Đã kết nối: {device} ({w}x{h})")
        else:
            self.ui.bot_error("Không tìm thấy thiết bị!")

    def _cmd_screen(self):
        self.ui.bot_say("📸 Đang chụp màn hình...")
        path = screenshot()
        self.ui.bot_success(f"Đã lưu: {path}")

    def _cmd_status(self):
        self.ui.bot_info(f"Engine: {self.detector.get_status()}")
        self.ui.bot_info(f"Đang record: {self.recorder.recording}")
        self.ui.bot_info(f"Đang play: {self.player.playing}")

    # ============================================================
    # LỆNH RECORD
    # ============================================================

    def _cmd_record(self, args):
        if self.player.playing:
            self.ui.bot_error("Đang phát macro. Gõ 'stop' trước.")
            return

        name = args if args else None
        self.recorder.start(name)
        self.ui.set_recording_state(True)

    def _cmd_stop(self):
        if self.recorder.recording:
            self.recorder.stop()
            self.ui.set_recording_state(False)
        elif self.player.playing:
            self.player.stop()
            self.ui.set_playing_state(False)
        else:
            self.ui.bot_say("Không có gì đang chạy.")

    # ============================================================
    # LỆNH REPLAY
    # ============================================================

    def _cmd_play(self, args):
        if not args:
            self.ui.bot_error("Cần tên macro. VD: play macro_001")
            self.player.list_macros()
            return

        if self.recorder.recording:
            self.ui.bot_error("Đang record. Gõ 'stop' trước.")
            return

        self.player.play(args)
        self.ui.set_playing_state(True)

    def _cmd_lap_forever(self, args):
        """Chay lap vo han den khi bam dung"""
        if not args:
            self.ui.bot_error("Can ten macro. VD: lap_forever macro_001")
            return
        if self.recorder.recording:
            self.ui.bot_error("Dang record. Go 'stop' truoc.")
            return
        self.ui.bot_say(f"Lap vo han: {args} (bam Dung de ngung)")
        self.player.play_lap_forever(args)
        self.ui.set_playing_state(True)

    def _cmd_loop(self, args):
        """Chạy lặp macro đến khi dừng"""
        if not args:
            self.ui.bot_error("Cần tên macro. VD: loop macro_001")
            return
        if self.recorder.recording:
            self.ui.bot_error("Đang record. Gõ 'stop' trước.")
            return

        self.ui.bot_say(f"🔁 Chạy lặp macro: {args} (bấm ⏹️ Dừng để dừng)")
        self.player.play_loop(args)
        self.ui.set_playing_state(True)

    def _cmd_seq(self, args):
        """Chạy tuần tự nhiều macro"""
        if not args:
            self.ui.bot_error("Cần ít nhất 1 tên macro. VD: seq macro1 macro2")
            return

        macro_names = args.split()
        self.ui.bot_say(f"▶️▶️ Chạy tuần tự {len(macro_names)} macro: {', '.join(macro_names)}")

        self.player.play_sequence(macro_names)
        self.ui.set_playing_state(True)

    def _cmd_delete(self, args):
        """Xóa macro"""
        if not args:
            self.ui.bot_error("Cần tên macro. VD: delete macro_001")
            self.player.list_macros()
            return

        from macro_manager import delete_macro
        if delete_macro(args):
            self.ui.bot_success(f"Đã xóa macro: {args}")
        else:
            self.ui.bot_error(f"Không tìm thấy macro: {args}")

    def _cmd_clear_dataset(self, args):
        """Xóa dataset (1 class hoặc tất cả)"""
        import shutil
        dataset_dir = PROJECT_DIR / "dataset"

        if args:
            class_dir = dataset_dir / args
            if class_dir.exists():
                shutil.rmtree(class_dir)
                self.ui.bot_success(f"Đã xóa dataset class: {args}")
            else:
                self.ui.bot_error(f"Không tìm thấy class: {args}")
        else:
            # Xóa tất cả
            for d in dataset_dir.iterdir():
                if d.is_dir():
                    shutil.rmtree(d)
            self.ui.bot_success("Đã xóa toàn bộ dataset")

    # ============================================================
    # LỆNH LIVE
    # ============================================================

    def _cmd_live_tap(self, label: str, args: str):
        """Click nút trực tiếp"""
        count = 1
        if args:
            try:
                count = int(args)
            except ValueError:
                pass

        self.ui.bot_say(f"🎯 Tìm nút \"{label}\" {count} lần...")

        for i in range(count):
            if count > 1:
                self.ui.bot_info(f"Lần {i+1}/{count}...")

            screen_path = screenshot()
            result = self.detector.detect(screen_path, label)

            if result:
                x, y, conf, engine = result
                tap(x, y)
                self.ui.bot_success(
                    f"✅ {label} tại ({x},{y}) [{engine}, {conf:.0%}]"
                )
            else:
                self.ui.bot_error(f"Không tìm thấy nút \"{label}\"")

    def _cmd_comment(self, args):
        """Comment text"""
        if not args:
            self.ui.bot_error("Cần nội dung comment. VD: comment xin chào")
            return

        # Tìm ô comment trước
        screen_path = screenshot()
        result = self.detector.detect(screen_path, "comment")

        if result:
            x, y, conf, engine = result
            tap(x, y)
            import time
            time.sleep(0.5)

        # Gõ text
        input_text(args)
        self.ui.bot_success(f"Đã comment: \"{args}\"")

    def _cmd_scroll(self):
        """Lướt video"""
        screen_w, screen_h = get_screen_size()
        x1 = screen_w // 2
        y1 = int(screen_h * 0.7)
        x2 = screen_w // 2
        y2 = int(screen_h * 0.3)
        swipe(x1, y1, x2, y2, 300)
        self.ui.bot_success("Đã lướt video tiếp")

    def _cmd_capture(self, args):
        """Xu ly click tu man hinh PC"""
        try:
            parts = args.split()
            x, y = int(parts[0]), int(parts[1])
            self.recorder._handle_touch(x, y)
        except (ValueError, IndexError):
            self.ui.bot_error("Lenh capture can 2 so: x y")

    def _cmd_tap(self, args):
        """Tap tọa độ trực tiếp"""
        try:
            parts = args.split()
            x, y = int(parts[0]), int(parts[1])
            tap(x, y)
            self.ui.bot_success(f"Đã tap ({x}, {y})")
        except (ValueError, IndexError):
            self.ui.bot_error("Cú pháp: tap <x> <y>")

    # ============================================================
    # LỆNH YOLO
    # ============================================================

    def _cmd_yolo(self, args):
        self.ui.bot_info(f"Engine: {self.detector.get_status()}")
        from macro_manager import get_dataset_stats
        stats = get_dataset_stats()
        if stats:
            total = sum(stats.values())
            self.ui.bot_info(f"Dataset: {total} ảnh, {len(stats)} class")
            for label, count in stats.items():
                self.ui.bot_info(f"  {label}: {count} ảnh")
            if total >= 50:
                self.ui.bot_info("💡 Đã đủ dữ liệu để train YOLO!")
                self.ui.bot_info("  Mở train_yolo/train.ipynb trên Colab để train")
        else:
            self.ui.bot_info("Dataset trống. Record thêm để tích lũy dữ liệu.")

    def _cmd_dataset(self):
        from macro_manager import get_dataset_stats
        stats = get_dataset_stats()
        if stats:
            self.ui.bot_info("📊 THỐNG KÊ DATASET:")
            total = sum(stats.values())
            for label, count in sorted(stats.items()):
                bar = "█" * min(count, 20)
                self.ui.bot_info(f"  {label:15s} {bar} {count}")
            self.ui.bot_info(f"  Tổng: {total} ảnh, {len(stats)} class")

            need = 50
            for label, count in stats.items():
                if count < need:
                    self.ui.bot_info(f"  ⚠️ '{label}' cần thêm {need-count} ảnh (hiện có {count})")
        else:
            self.ui.bot_info("Dataset trống. Gõ 'record' để bắt đầu thu thập dữ liệu.")

    def run(self):
        """Chạy app"""
        self.ui.run()


if __name__ == "__main__":
    bot = TikTokBot()
    bot.run()
