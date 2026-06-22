"""
ADB Utilities - giao tiếp với điện thoại Android qua ADB
Sử dụng adb.exe có sẵn trong thư mục scrcpy/
"""

import os
import subprocess
import time
from pathlib import Path

# Đường dẫn tới adb.exe (cùng thư mục scrcpy trong project)
PROJECT_DIR = Path(__file__).parent
ADB_PATH = PROJECT_DIR / "scrcpy" / "adb.exe"


def _adb(cmd: str, timeout: int = 10) -> str:
    """Chạy lệnh ADB và trả về output"""
    full_cmd = f'"{ADB_PATH}" {cmd}'
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if result.returncode != 0 and result.stderr:
        return result.stderr.strip()
    return result.stdout.strip()


def check_device() -> str | None:
    """Kiểm tra thiết bị đã kết nối chưa. Trả về serial hoặc None"""
    output = _adb("devices")
    lines = output.split("\n")[1:]  # Bỏ dòng header
    for line in lines:
        if "\tdevice" in line:
            return line.split("\t")[0]
    return None


def screenshot(save_path: str = None) -> str:
    """
    Chụp màn hình điện thoại và lưu vào file.
    Trả về đường dẫn file ảnh.
    """
    if save_path is None:
        save_path = str(PROJECT_DIR / "screenshots" / f"screen_{int(time.time()*1000)}.png")

    # Đảm bảo là đường dẫn tuyệt đối
    save_path = os.path.abspath(save_path)

    # Đảm bảo thư mục tồn tại
    save_dir = os.path.dirname(save_path)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    # Chụp màn hình và lưu trực tiếp ra file
    # Dùng exec-out screencap -p để lấy ảnh raw
    full_cmd = f'"{ADB_PATH}" exec-out screencap -p > "{save_path}"'
    subprocess.run(full_cmd, shell=True, timeout=10)

    return save_path


def tap(x: int, y: int):
    """Chạm vào tọa độ (x, y) trên màn hình"""
    _adb(f"shell input tap {x} {y}")


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
    """Vuốt từ (x1,y1) đến (x2,y2) trong duration_ms mili giây"""
    _adb(f"shell input swipe {x1} {y1} {x2} {y2} {duration_ms}")


def input_text(text: str):
    """Gõ text vào điện thoại (hỗ trợ tiếng Việt có dấu qua clipboard)"""
    # ADB input text không hỗ trợ tiếng Việt có dấu tốt
    # Dùng clipboard làm trung gian
    escaped = text.replace('"', '\\"').replace("'", "\\'")
    # Thử input text trực tiếp trước
    _adb(f'shell input text "{escaped}"')


def input_text_via_clipboard(text: str):
    """Gõ text qua clipboard (hỗ trợ Unicode tốt hơn)"""
    import base64
    # Mã hóa text thành base64 để tránh vấn đề escaping
    encoded = base64.b64encode(text.encode('utf-8')).decode('ascii')
    # Dùng service call để set clipboard rồi paste
    _adb(f'shell am broadcast -a clipper.set -e text "{text}"')
    # Cách khác: dùng cmd clipboard
    _adb(f'shell "echo {encoded} | base64 -d | clipservice"')
    # Paste
    _adb("shell input keyevent 279")  # KEYCODE_PASTE


def input_keyevent(keycode: int):
    """Gửi key event (phím Android)"""
    _adb(f"shell input keyevent {keycode}")


def get_screen_size() -> tuple[int, int]:
    """Lấy kích thước màn hình (width, height)"""
    output = _adb("shell wm size")
    # Output dạng: "Physical size: 1080x2400"
    size_str = output.split(":")[-1].strip()
    w, h = size_str.split("x")
    return int(w), int(h)


def get_touch_device() -> str | None:
    """Tìm device path của màn hình cảm ứng"""
    output = _adb("shell getevent -p")
    lines = output.split("\n")
    current_device = None
    for line in lines:
        if line.startswith("add device"):
            current_device = line.split(":")[1].strip()
        if current_device and ("ABS_MT_POSITION_X" in line or "touch" in line.lower()):
            return current_device
    # Fallback: thử tìm device có ABS_MT
    current_device = None
    for line in lines:
        if line.startswith("add device"):
            current_device = line.split(":")[1].strip()
        if current_device and "ABS_MT_POSITION_X" in line:
            return current_device
    return None


def getevent_stream():
    """
    Generator: lắng nghe sự kiện chạm từ điện thoại.
    Yield (event_type, x, y) khi có sự kiện.
    event_type: 'down', 'up'
    """
    device = get_touch_device()
    if not device:
        for dev in ["/dev/input/event0", "/dev/input/event1", "/dev/input/event2",
                     "/dev/input/event3", "/dev/input/event4", "/dev/input/event5"]:
            try:
                _adb(f"shell getevent -l {dev}")
                device = dev
                break
            except:
                continue

    if not device:
        raise RuntimeError("Không tìm thấy thiết bị cảm ứng!")

    cmd = f'"{ADB_PATH}" shell getevent -l {device}'
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    current_x = 0
    current_y = 0
    is_down = False
    new_down_detected = False  # Mới phát hiện DOWN, chờ SYN_REPORT

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            parts = line.split()

            # Parse ABS_MT_POSITION_X
            if "ABS_MT_POSITION_X" in line:
                try:
                    val = parts[-1]
                    current_x = int(val, 16) if val.isalnum() else int(val)
                except (ValueError, IndexError):
                    pass

            # Parse ABS_MT_POSITION_Y
            elif "ABS_MT_POSITION_Y" in line:
                try:
                    val = parts[-1]
                    current_y = int(val, 16) if val.isalnum() else int(val)
                except (ValueError, IndexError):
                    pass

            # BTN_TOUCH DOWN → đánh dấu có touch mới, đợi SYN_REPORT mới yield
            elif "BTN_TOUCH" in line and "DOWN" in line:
                if not is_down:
                    is_down = True
                    new_down_detected = True

            elif "BTN_TOUCH" in line and "UP" in line:
                if is_down:
                    is_down = False
                    yield ("up", current_x, current_y)

            # ABS_MT_TRACKING_ID
            elif "ABS_MT_TRACKING_ID" in line:
                try:
                    val = parts[-1]
                    if "ffffff" in val.lower():
                        if is_down:
                            is_down = False
                            yield ("up", current_x, current_y)
                    else:
                        if not is_down:
                            is_down = True
                            new_down_detected = True
                except (ValueError, IndexError):
                    pass

            # SYN_REPORT: kết thúc gói → lúc này X,Y đã được cập nhật đầy đủ
            elif "SYN_REPORT" in line:
                if new_down_detected:
                    new_down_detected = False
                    yield ("down", current_x, current_y)

    finally:
        process.terminate()
        process.wait()


# === File operations ===

def list_files(remote_path: str = "/sdcard/") -> list[dict]:
    """Liệt kê file/thư mục trên điện thoại. Trả về list[dict]"""
    # Dùng ls -la để lấy chi tiết
    output = _adb(f'shell ls -la "{remote_path}"')
    files = []
    lines = output.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("total"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        # Format: drwxrwx--- 2 root sdcard_rw 4096 2026-06-20 12:00 file.mp4
        # Hoặc: -rwxrwx--- 1 root sdcard_rw 123456 2026-06-20 12:00 file.mp4
        try:
            perms = parts[0]
            is_dir = perms.startswith("d")
            name = " ".join(parts[7:]) if len(parts) > 7 else parts[-1]
            size = int(parts[4]) if len(parts) > 5 else 0
            # Parse thời gian
            date_str = f"{parts[5]} {parts[6]}" if len(parts) > 6 else ""
            files.append({
                "name": name,
                "is_dir": is_dir,
                "size": size,
                "date": date_str,
                "path": f"{remote_path.rstrip('/')}/{name}",
            })
        except (ValueError, IndexError):
            continue
    # Sắp xếp: thư mục trước, file sau
    files.sort(key=lambda f: (not f["is_dir"], f["name"].lower()))
    return files


def _escape_path(path: str) -> str:
    """Escape ký tự đặc biệt cho Android shell"""
    # Escape ( ) [ ] & ; | $ ` ' " < > space
    import re
    return re.sub(r"([()\[\]&;|$`'\"<> ])", r"\\\1", path)


def delete_remote(path: str) -> bool:
    """Xóa file hoặc thư mục trên điện thoại"""
    escaped = _escape_path(path)
    output = _adb(f"shell rm -rf {escaped}")
    return "error" not in output.lower()


def pull_file(remote_path: str, local_path: str) -> bool:
    """Kéo file từ điện thoại về máy tính"""
    import subprocess
    escaped = _escape_path(remote_path)
    cmd = f'"{ADB_PATH}" pull "{escaped}" "{local_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return result.returncode == 0


def push_file(local_path: str, remote_path: str) -> bool:
    """Đẩy file từ máy tính lên điện thoại"""
    import subprocess
    escaped = _escape_path(remote_path)
    cmd = f'"{ADB_PATH}" push "{local_path}" "{escaped}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    return result.returncode == 0


def get_file_info(remote_path: str) -> dict | None:
    """Lấy thông tin 1 file"""
    output = _adb(f'shell ls -la "{remote_path}"')
    if not output or "No such file" in output:
        return None
    # Trả về thông tin cơ bản
    return {"path": remote_path, "exists": True}


def make_dir(remote_path: str) -> bool:
    """Tạo thư mục trên điện thoại"""
    output = _adb(f'shell mkdir -p "{remote_path}"')
    return "error" not in output.lower()


# === KeyEvent constants cho Android ===
KEYCODE_HOME = 3
KEYCODE_BACK = 4
KEYCODE_ENTER = 66
KEYCODE_DEL = 67
KEYCODE_PASTE = 279
KEYCODE_DPAD_UP = 19
KEYCODE_DPAD_DOWN = 20
