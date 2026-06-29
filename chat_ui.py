"""
Giao diện chat Tkinter - cửa sổ giao tiếp với bot
"""

import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext, filedialog, messagebox, simpledialog
from datetime import datetime
import threading
import queue
from PIL import Image, ImageTk
import os
from pathlib import Path

PROJECT_DIR = Path(__file__).parent


class ChatUI:
    """Cửa sổ chat chính"""

    def __init__(self, title: str = "TikTok Auto Bot"):
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("980x850")
        self.root.minsize(650, 650)
        self.root.configure(bg="#1e1e1e")

        self.command_callback = None
        self.popup_queue = queue.Queue()
        self.recording = False
        self.playing = False
        self._scrcpy_process = None
        self._nav_win = None
        self._thumb_refs = []

        self._build_ui()
        self._poll_popup_queue()

    def _build_ui(self):
        """Xây dựng giao diện"""
        header = tk.Frame(self.root, bg="#2d2d2d", height=40)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        self.status_label = tk.Label(
            header, text="San sang | Template Matching",
            bg="#2d2d2d", fg="#a0a0a0",
            font=("Consolas", 9), anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=8)

        # Cac nut
        self.record_btn = tk.Button(
            header, text="Ghi", command=self._toggle_record,
            bg="#8b0000", fg="white",
            font=("Consolas", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=10,
        )
        self.record_btn.pack(side=tk.RIGHT, padx=3, pady=6)

        self.play_btn = tk.Button(
            header, text="Phat", command=self._toggle_play,
            bg="#0e639c", fg="white",
            font=("Consolas", 9, "bold"), relief=tk.FLAT, cursor="hand2", width=10,
        )
        self.play_btn.pack(side=tk.RIGHT, padx=3, pady=6)

        btn_data = [
            ("Macro", self._open_macro_manager),
            ("Dataset", self._open_dataset_manager),
            ("Files", self._open_file_manager),
            ("Click", self._capture_click),
            ("ScrOff", self._toggle_scroff),
            ("Scroll", self._toggle_autoscroll),
        ]
        # Add Bac/Hom/Rec buttons in header
        nav_frame = tk.Frame(header, bg="#2d2d2d")
        nav_frame.pack(side=tk.RIGHT, padx=3, pady=6)
        for txt, cmd in [("Bac", self._key_back), ("Hom", self._key_home), ("Rec", self._key_recent)]:
            tk.Button(nav_frame, text=txt, command=cmd, bg="#3c3c3c", fg="#d4d4d4",
                      font=("Consolas", 9), relief=tk.FLAT, cursor="hand2", width=4).pack(side=tk.LEFT, padx=1)
        for text, cmd in btn_data:
            tk.Button(
                header, text=text, command=cmd,
                bg="#3c3c3c", fg="#d4d4d4",
                font=("Consolas", 9), relief=tk.FLAT, cursor="hand2",
            ).pack(side=tk.RIGHT, padx=3, pady=6)

        # Khung chua dien thoai + chat
        # Chat area
        chat_frame = tk.Frame(self.root, bg="#1e1e1e")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4", font=("Consolas", 10),
            state=tk.DISABLED, relief=tk.FLAT, borderwidth=0,
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        for tag, color in [
            ("bot", "#4ec9b0"), ("user", "#569cd6"), ("error", "#f44747"),
            ("success", "#6a9955"), ("info", "#ce9178"), ("timestamp", "#808080")
        ]:
            self.chat_display.tag_config(tag, foreground=color)

        # Input
        input_frame = tk.Frame(self.root, bg="#2d2d2d", height=45)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
        input_frame.pack_propagate(False)

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_frame, textvariable=self.input_var,
            bg="#3c3c3c", fg="#d4d4d4", insertbackground="#d4d4d4",
            font=("Consolas", 11), relief=tk.FLAT,
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 3), pady=5)
        self.input_entry.bind("<Return>", lambda e: self._send_message())
        self.input_entry.focus_set()

        tk.Button(
            input_frame, text="Gui", command=self._send_message,
            bg="#0e639c", fg="white",
            font=("Consolas", 10, "bold"), relief=tk.FLAT, cursor="hand2", width=8,
        ).pack(side=tk.RIGHT, padx=(0, 5), pady=5)

        self.root.bind("<Control-l>", lambda e: self.input_entry.focus_set())

    # === QUEUE ===

    def _poll_popup_queue(self):
        try:
            while True:
                cb = self.popup_queue.get_nowait()
                try:
                    cb()
                except Exception as e:
                    print(f"[QUEUE] {e}")
                self.popup_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_popup_queue)

    def set_command_callback(self, callback):
        self.command_callback = callback

    def _toggle_record(self):
        if self.recording:
            self.command_callback and self.command_callback("stop")
        else:
            self.command_callback and self.command_callback("record")

    def _toggle_play(self):
        if self.playing:
            self.command_callback and self.command_callback("stop")
        else:
            self._open_play_popup()

    # === PLAY POPUP ===

    def _open_play_popup(self):
        from macro_manager import list_macros
        macros = list_macros()
        if not macros:
            self.bot_error("Chua co macro nao!")
            return

        win = tk.Toplevel(self.root)
        win.title("Chon Macro de Phat")
        win.geometry("400x350")
        win.configure(bg="#2d2d2d")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Chon macro:", bg="#2d2d2d", fg="#ffffff",
                 font=("Consolas", 11, "bold")).pack(pady=10)

        cf = tk.Frame(win, bg="#2d2d2d")
        cf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas = tk.Canvas(cf, bg="#2d2d2d", highlightthickness=0)
        sb = tk.Scrollbar(cf, orient=tk.VERTICAL, command=canvas.yview)
        sf = tk.Frame(canvas, bg="#2d2d2d")
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        for mn in macros:
            row = tk.Frame(sf, bg="#3c3c3c", pady=5)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=mn, bg="#3c3c3c", fg="#d4d4d4",
                     font=("Consolas", 10), anchor="w", width=25).pack(side=tk.LEFT, padx=8)
            def do_play(n=mn):
                self.command_callback and self.command_callback(f"play {n}")
                win.destroy()
            def do_chay_het(n=mn):
                self.command_callback and self.command_callback(f"loop {n}")
                win.destroy()
            tk.Button(row, text="Chay het", command=do_chay_het,
                      bg="#8b4513", fg="white",
                      font=("Consolas", 9), relief=tk.FLAT, cursor="hand2", width=8
                      ).pack(side=tk.RIGHT, padx=2)
            tk.Button(row, text="Phat", command=do_play,
                      bg="#0e639c", fg="white",
                      font=("Consolas", 9), relief=tk.FLAT, cursor="hand2", width=8
                      ).pack(side=tk.RIGHT, padx=2)

        def _on_mw(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mw)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        tk.Button(win, text="Dong", command=win.destroy,
                  bg="#5a5a5a", fg="white",
                  font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=10).pack(pady=10)

    def set_recording_state(self, active: bool):
        self.recording = active
        self.record_btn.config(text="Dung" if active else "Ghi",
                                bg="#006600" if active else "#8b0000")

    def set_playing_state(self, active: bool):
        self.playing = active
        self.play_btn.config(text="Dung" if active else "Phat",
                              bg="#cc6600" if active else "#0e639c")

    # === CHAT MESSAGES ===

    def _send_message(self):
        text = self.input_var.get().strip()
        if not text:
            return
        self.input_var.set("")
        self._add_message("Ban", text, "user")
        self.command_callback and self.command_callback(text)

    def _add_message(self, sender: str, text: str, tag: str):
        self.chat_display.config(state=tk.NORMAL)
        now = datetime.now().strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{now}] ", "timestamp")
        self.chat_display.insert(tk.END, f"[{sender}]: ", tag)
        self.chat_display.insert(tk.END, f"{text}\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def bot_say(self, text, tag="bot"):
        self._add_message("Bot", text, tag)

    def bot_error(self, text):
        self._add_message("Bot", f"Loi: {text}", "error")

    def bot_success(self, text):
        self._add_message("Bot", f"OK: {text}", "success")

    def bot_info(self, text):
        self._add_message("Bot", text, "info")

    def update_status(self, text):
        self.status_label.config(text=text)

    # === POPUP ===

    def show_popup(self, title: str, prompt: str, callback):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry("350x160")
        popup.configure(bg="#2d2d2d")
        popup.transient(self.root)
        popup.grab_set()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))

        popup.update_idletasks()
        mx = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
        my = self.root.winfo_y() + (self.root.winfo_height() - 160) // 2
        popup.geometry(f"+{max(0, mx)}+{max(0, my)}")

        tk.Label(popup, text=prompt, bg="#2d2d2d", fg="#d4d4d4",
                 font=("Consolas", 10)).pack(pady=(15, 5))

        var = tk.StringVar()
        entry = tk.Entry(popup, textvariable=var, bg="#3c3c3c", fg="#d4d4d4",
                         insertbackground="#d4d4d4", font=("Consolas", 12),
                         relief=tk.FLAT, width=25)
        entry.pack(pady=5, padx=20)
        entry.focus_set()

        bf = tk.Frame(popup, bg="#2d2d2d")
        bf.pack(pady=10)

        def ok():
            v = var.get().strip()
            popup.destroy()
            callback and callback(v)

        def skip():
            popup.destroy()
            callback and callback(None)

        def stop():
            popup.destroy()
            callback and callback("__STOP__")

        tk.Button(bf, text="OK", command=ok, bg="#0e639c", fg="white",
                  font=("Consolas", 10, "bold"), relief=tk.FLAT, cursor="hand2", width=8
                  ).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Bo qua", command=skip, bg="#5a5a5a", fg="white",
                  font=("Consolas", 9), relief=tk.FLAT, cursor="hand2", width=8
                  ).pack(side=tk.LEFT, padx=3)
        tk.Button(bf, text="Dung", command=stop, bg="#8b0000", fg="white",
                  font=("Consolas", 9), relief=tk.FLAT, cursor="hand2", width=8
                  ).pack(side=tk.LEFT, padx=3)

        entry.bind("<Return>", lambda e: ok())
        popup.bind("<Escape>", lambda e: skip())
        return popup

    def request_popup(self, title: str, prompt: str, callback):
        self.popup_queue.put(lambda: self.show_popup(title, prompt, callback))


    # === CAPTURE CLICK ===

    def _capture_click(self):
        from adb_utils import screenshot, tap as adb_tap, get_screen_size
        path = screenshot()
        if not path or not os.path.exists(path):
            self.bot_error("Khong the chup man hinh")
            return
        img = Image.open(path)
        screen_w, screen_h = img.size
        win = tk.Toplevel(self.root)
        win.title("Click vao vi tri can ghi")
        win.configure(bg="#1e1e1e")
        win.transient(self.root)
        display_w = min(img.width, 360)
        display_h = int(img.height * (display_w / img.width))
        img_resized = img.resize((display_w, display_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_resized)
        lbl = tk.Label(win, image=tk_img, bg="#000000", cursor="crosshair", width=display_w, height=display_h)
        lbl.image = tk_img
        lbl.pack(padx=0, pady=0)
        def on_click(event):
            px = int(event.x * screen_w / display_w)
            py = int(event.y * screen_h / display_h)
            win.destroy()
            adb_tap(px, py)
            self.command_callback and self.command_callback(f"capture {px} {py}")
        lbl.bind("<ButtonRelease-1>", on_click, "+")
        win.wait_visibility()
        win.update()
        bf = tk.Frame(win, bg="#1e1e1e")
        bf.pack(pady=5)
        tk.Button(bf, text="Huy", command=win.destroy,
                  bg="#5a5a5a", fg="white",
                  font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=10).pack()

    # === CAPTURE COORDINATES ===

    def _capture_coordinates(self, x_var, y_var):
        """LOC: giong Click nhung cap nhat X,Y vao o"""
        from adb_utils import screenshot, get_screen_size
        import os as _os
        path = screenshot()
        if not path or not _os.path.exists(path):
            self.bot_error("Khong the chup man hinh")
            return
        img = Image.open(path)
        screen_w, screen_h = img.size
        win = tk.Toplevel(self.root)
        win.title("Click chon toa do (LOC)")
        win.configure(bg="#1e1e1e")
        win.transient(self.root)
        win.grab_set()
        display_w = min(img.width, 360)
        display_h = int(img.height * (display_w / img.width))
        img_resized = img.resize((display_w, display_h), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(img_resized)
        lbl = tk.Label(win, image=tk_img, bg="#000000", cursor="crosshair", width=display_w, height=display_h)
        lbl.image = tk_img
        lbl.pack(padx=0, pady=0)
        def on_click(event):
            px = int(event.x * screen_w / display_w)
            py = int(event.y * screen_h / display_h)
            x_var.set(str(px))
            y_var.set(str(py))
            self.bot_say(f"Toa do moi: X={px}, Y={py}")
            self.root.update_idletasks()
            win.destroy()
        lbl.bind("<Button-1>", on_click)
        win.wait_visibility()
        win.update()
        bf = tk.Frame(win, bg="#1e1e1e")
        bf.pack(pady=5)
        tk.Button(bf, text="Huy", command=win.destroy,
                  bg="#5a5a5a", fg="white",
                  font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=10).pack()
    def _editor_add_step_at(self, idx):
        """Them 1 buoc moi - luu truoc, them sau, mo lai"""
        if not hasattr(self, '_editor_steps') or self._editor_steps is None:
            return
        # Luu cac chinh sua hien tai
        if hasattr(self, '_do_save') and callable(self._do_save):
            self._do_save()
        from macro_manager import save_macro, load_macro
        macro = load_macro(self._editor_name)
        if not macro: return
        st = macro.get("steps", [])
        if idx >= len(st): idx = len(st) - 1
        ts = (st[idx]["timestamp"] + 5.0) if st else 5.0
        st.insert(idx+1, {"timestamp": ts, "type": "tap", "label": "buoc moi",
            "x": 0, "y": 0, "coords": [[0, 0]],
            "screen_w": 720, "screen_h": 1280, "image_crop": ""})
        save_macro(self._editor_name, st)
        if hasattr(self, '_editor_win') and self._editor_win:
            self._editor_win.destroy()
        if hasattr(self, '_editor_name'):
            self._open_macro_editor(self._editor_name)

    def _toggle_autoscroll(self):
        """Tu dong vuot TikTok voi thoi gian ngau nhien"""
        import random, time, threading
        if hasattr(self, '_autoscroll_active') and self._autoscroll_active:
            self._autoscroll_active = False
            self.bot_say("Da dung tu dong vuot")
            return
        self._autoscroll_active = True
        self.bot_say("Bat dau tu dong vuot TikTok...")
        def run():
            from adb_utils import swipe, get_screen_size
            _, h = get_screen_size()
            while self._autoscroll_active:
                delay = random.uniform(15, 45)
                self.bot_say(f"Cho {delay:.0f}s roi vuot...")
                time.sleep(delay)
                if not self._autoscroll_active: break
                cx = 360
                swipe(cx, int(h*0.7), cx, int(h*0.3), 300)
                self.bot_say(f"Da vuot (cho {delay:.0f}s)")
            self.bot_say("Da dung")
        threading.Thread(target=run, daemon=True).start()

    # === KEY EVENTS ===

    def _key_back(self):
        from adb_utils import _adb
        _adb("shell input keyevent 4")
        self.bot_say("Back")

    def _key_home(self):
        from adb_utils import _adb
        _adb("shell input keyevent 3")
        self.bot_say("Home")

    def _key_recent(self):
        from adb_utils import _adb
        _adb("shell input keyevent 187")
        self.bot_say("Recent")

    # === SCRCPY ===

    def _show_nav_bar(self):
        """Cua so nho: Back, Home, Recent"""
        if hasattr(self, '_nav_win') and self._nav_win:
            return
        self._nav_win = tk.Toplevel(self.root)
        self._nav_win.title("nav")
        self._nav_win.configure(bg="#2d2d2d")
        self._nav_win.overrideredirect(True)
        self._nav_win.attributes("-topmost", True)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._nav_win.geometry(f"280x45+{sw-290}+{sh-50}")
        for txt, cmd in [("Back", self._key_back), ("Home", self._key_home), ("Rec", self._key_recent)]:
            tk.Button(self._nav_win, text=txt, command=cmd,
                      bg="#3c3c3c", fg="#d4d4d4",
                      font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=8
                      ).pack(side=tk.LEFT, padx=4, pady=5)

    def _hide_nav_bar(self):
        if hasattr(self, '_nav_win') and self._nav_win:
            self._nav_win.destroy()
            self._nav_win = None

    def _toggle_scroff(self):
        import subprocess
        from pathlib import Path
        if self._scrcpy_process:
            self._scrcpy_process.kill()
            self._scrcpy_process = None
            self._hide_nav_bar()
            self.bot_say("Da dong scrcpy")
            return
        p = Path(__file__).parent / "scrcpy" / "scrcpy.exe"
        if not p.exists():
            self.bot_error("Khong tim thay scrcpy")
            return
        try:
            subprocess.run([str(p.parent / "adb.exe"), "start-server"], capture_output=True, timeout=5)
            self._scrcpy_process = subprocess.Popen([str(p), "--turn-screen-off"], cwd=str(p.parent),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.bot_success("Da mo scrcpy")
        except Exception as e:
            self.bot_error(f"Loi: {e}")



    # === MACRO MANAGER ===

    def _open_macro_manager(self):
        from macro_manager import list_macros, delete_macro
        macros = list_macros()
        win = tk.Toplevel(self.root)
        win.title("Quan ly Macro")
        win.geometry("750x550")
        win.minsize(600, 400)
        win.configure(bg="#2d2d2d")
        win.transient(self.root)
        win.grab_set()
        win.update_idletasks()
        mx = self.root.winfo_x() + (self.root.winfo_width() - 750) // 2
        my = self.root.winfo_y() + (self.root.winfo_height() - 550) // 2
        win.geometry(f"+{max(0, mx)}+{max(0, my)}")
        tk.Label(win, text="Danh sach Macro", bg="#2d2d2d", fg="#ffffff",
                 font=("Consolas", 12, "bold")).pack(pady=10)
        if not macros:
            tk.Label(win, text="(chua co macro nao)", bg="#2d2d2d", fg="#808080",
                     font=("Consolas", 10)).pack(pady=30)
            tk.Button(win, text="Dong", command=win.destroy,
                      bg="#5a5a5a", fg="white",
                      font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=10).pack()
            return
        cf = tk.Frame(win, bg="#2d2d2d")
        cf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(cf, bg="#2d2d2d", highlightthickness=0)
        sb = tk.Scrollbar(cf, orient=tk.VERTICAL, command=canvas.yview)
        sf = tk.Frame(canvas, bg="#2d2d2d")
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw", width=710)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        seq_vars = []
        def do_copy(name):
            from macro_manager import load_macro, save_macro
            m = load_macro(name)
            if m:
                save_macro(name + "_copy", m["steps"])
                win.destroy()
                self._open_macro_manager()
        def do_play(name):
            win.destroy()
            self.command_callback and self.command_callback("play " + name)
        def do_edit(name):
            win.destroy()
            self._open_macro_editor(name)
        def do_delete(name, row):
            delete_macro(name)
            row.destroy()
            if not list_macros():
                win.destroy()
        for mn in macros:
            row = tk.Frame(sf, bg="#3c3c3c", pady=5)
            row.pack(fill=tk.X, pady=2)
            var = tk.BooleanVar(value=False)
            seq_vars.append((mn, var))
            tk.Checkbutton(row, variable=var, bg="#3c3c3c",
                           activebackground="#3c3c3c", selectcolor="#2d2d2d").pack(side=tk.LEFT, padx=2)
            tk.Label(row, text=mn, bg="#3c3c3c", fg="#d4d4d4",
                     font=("Consolas", 10), anchor="w", width=22).pack(side=tk.LEFT, padx=5)
            def do_chayhet(n=mn):
                self.command_callback and self.command_callback(f"loop {n}")
                win.destroy()
            for t, cmd in [("Sua", do_edit), ("Copy", do_copy), ("Chay het", do_chayhet), ("Play", do_play), ("Xoa", do_delete)]:
                tk.Button(row, text=t,
                          command=(lambda n=mn, f=cmd: f(n)) if t != "Xoa" else (lambda n=mn, r=row, f=cmd: f(n, r)),
                          bg="#8b4513" if t=="Chay het" else "#0e639c" if t=="Play" else "#5a5a5a" if t!="Xoa" else "#8b0000",
                          fg="white", font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=8
                          ).pack(side=tk.RIGHT, padx=2)
        def run_seq():
            selected = [n for n,v in seq_vars if v.get()]
            if not selected: return
            win.destroy()
            self.command_callback and self.command_callback("seq " + " ".join(selected))
        def _on_mw(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mw)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())
        bf = tk.Frame(win, bg="#2d2d2d")
        bf.pack(pady=10)
        tk.Button(bf, text="Chay nhieu macro", command=run_seq,
                  bg="#0e639c", fg="white", font=("Consolas",10,"bold"), relief=tk.FLAT, cursor="hand2", width=20
                  ).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Dong", command=win.destroy,
                  bg="#5a5a5a", fg="white", font=("Consolas",10), relief=tk.FLAT, cursor="hand2", width=10
                  ).pack(side=tk.LEFT, padx=5)


    def _open_macro_editor(self, name):
        from macro_manager import load_macro, save_macro
        macro = load_macro(name)
        if not macro:
            self.bot_error("Khong tim thay macro: " + name)
            return
        steps = macro.get("steps", [])
        win = tk.Toplevel(self.root)
        win.title("Sua Macro: " + name)
        win.geometry("900x650")
        win.minsize(700, 400)
        win.configure(bg="#2d2d2d")
        win.transient(self.root)
        win.grab_set()
        win.update_idletasks()
        mx = self.root.winfo_x() + (self.root.winfo_width() - 900) // 2
        my = self.root.winfo_y() + (self.root.winfo_height() - 650) // 2
        win.geometry(f"+{max(0, mx)}+{max(0, my)}")
        tk.Label(win, text=name + " - " + str(len(steps)) + " buoc",
                 bg="#2d2d2d", fg="#ffffff",
                 font=("Consolas", 12, "bold")).pack(pady=(10, 0))
        cf = tk.Frame(win, bg="#2d2d2d")
        cf.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(cf, bg="#2d2d2d", highlightthickness=0)
        sb = tk.Scrollbar(cf, orient=tk.VERTICAL, command=canvas.yview)
        sf = tk.Frame(canvas, bg="#2d2d2d")
        sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw", width=860)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        ch = tk.Frame(sf, bg="#3c3c3c", pady=3)
        ch.pack(fill=tk.X, pady=(0, 2))
        for ct, cw in [("#", 3), ("Chenh(s)", 10), ("Loai", 6), ("Huong", 5), ("Toc do", 7), ("Nhan", 14),
                        ("X", 5), ("Y", 5), ("Hanh dong", 10)]:
            tk.Label(ch, text=ct, bg="#3c3c3c", fg="#808080",
                     font=("Consolas", 8), anchor="w", width=cw).pack(side=tk.LEFT, padx=1)

        import tkinter.ttk as ttk
        edit_vars = []
        for i, step in enumerate(steps):
            container = tk.Frame(sf, bg="#2d2d2d")
            container.pack(fill=tk.X, pady=1)
            row = tk.Frame(container, bg="#3c3c3c" if i%2==0 else "#363636", pady=2)
            row.pack(fill=tk.X)
            tk.Label(row, text=" " + str(i+1), bg=row["bg"], fg="#808080",
                     font=("Consolas",9), width=3, anchor="w").pack(side=tk.LEFT)
            pv = steps[i-1]["timestamp"] if i>0 else 0
            delay = round(step["timestamp"] - pv, 2) if "timestamp" in step else 0
            sv = {"orig": step, "ts": tk.StringVar(value=str(delay) if delay<=0 else "{:.1f}".format(delay)),
                  "label": tk.StringVar(value=step.get("label","")),
                  "type_var": tk.StringVar(value=step.get("type","tap")),
                  "dir_var": tk.StringVar(value=step.get("direction","up")),
                  "len_var": tk.StringVar(value=step.get("length","5")),
                  "text_var": tk.StringVar(value=step.get("text_content","")),
                  "clear_var": tk.BooleanVar(value=step.get("clear_first",False))}
            tk.Entry(row, textvariable=sv["ts"], bg="#2d2d2d", fg="#d4d4d4",
                     font=("Consolas",9), width=10, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
            ttc = ttk.Combobox(row, textvariable=sv["type_var"], values=("tap","swipe","text"),
                               width=5, font=("Consolas",8), state="readonly")
            ttc.pack(side=tk.LEFT, padx=1)
            sw_frame = tk.Frame(row, bg=row["bg"])
            sw_frame.pack(side=tk.LEFT)
            tdc = ttk.Combobox(sw_frame, textvariable=sv["dir_var"], values=("up","down","left","right"),
                               width=4, font=("Consolas",8), state="readonly")
            tdc.pack(side=tk.LEFT, padx=1)
            tlc = ttk.Combobox(sw_frame, textvariable=sv["len_var"],
                values=("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
                width=4, font=("Consolas",8), state="readonly")
            tlc.pack(side=tk.LEFT, padx=1)
            label_entry = tk.Entry(row, textvariable=sv["label"], bg="#2d2d2d", fg="#4ec9b0",
                     font=("Consolas",9,"bold"), width=14, relief=tk.FLAT)
            label_entry.pack(side=tk.LEFT, padx=1)
            text_frame = tk.Frame(row, bg=row["bg"])
            text_frame.pack(side=tk.LEFT)
            text_clear_cb = tk.Checkbutton(text_frame, text="Xoa cu", variable=sv["clear_var"],
                                            bg=row["bg"], fg="#808080",
                                            font=("Consolas",8), selectcolor="#2d2d2d")
            text_clear_cb.pack(side=tk.LEFT)
            text_entry = tk.Entry(text_frame, textvariable=sv["text_var"], bg="#2d2d2d", fg="#ce9178",
                                   font=("Consolas",9), width=15, relief=tk.FLAT)
            text_entry.pack(side=tk.LEFT, padx=1)
            def toggle_type(*a):
                t = sv["type_var"].get()
                if t == "swipe":
                    sw_frame.pack(before=label_entry)
                    text_frame.pack_forget()
                elif t == "text":
                    sw_frame.pack_forget()
                    text_frame.pack(before=mxv_entry)
                else:  # tap
                    sw_frame.pack_forget()
                    text_frame.pack_forget()
            sv["type_var"].trace_add("write", toggle_type)
            coords = step.get("coords", [[step.get("x",0), step.get("y",0)]])
            extra_vars = []
            ec = tk.Frame(container, bg="#2d2d2d")
            def mk_cr(par, cx, cy, cname="", ctype="tap", cdir="up", clen="400"):
                cr = tk.Frame(par, bg="#2a2a2a", pady=1)
                cr.pack(fill=tk.X)
                tk.Label(cr, text="", bg="#2a2a2a", width=45).pack(side=tk.LEFT)
                nv = tk.StringVar(value=cname)
                xv = tk.StringVar(value=str(cx))
                yv = tk.StringVar(value=str(cy))
                tv = tk.StringVar(value=ctype)
                dv = tk.StringVar(value=cdir)
                lv = tk.StringVar(value=clen)
                vt = [nv, xv, yv, cr, tv, dv, lv]
                if cname or par != row:
                    tk.Entry(cr, textvariable=nv, bg="#1e1e1e", fg="#ce9178",
                             font=("Consolas",9), width=12, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
                ttc2 = ttk.Combobox(cr, textvariable=tv, values=("tap","swipe","text"),
                                    width=4, font=("Consolas",8), state="readonly")
                ttc2.pack(side=tk.LEFT, padx=1)
                swf = tk.Frame(cr, bg="#2a2a2a")
                swf.pack(side=tk.LEFT)
                tdc2 = ttk.Combobox(swf, textvariable=dv, values=("up","down","left","right"),
                                    width=3, font=("Consolas",8), state="readonly")
                tdc2.pack(side=tk.LEFT, padx=1)
                tlc2 = ttk.Combobox(swf, textvariable=lv,
                    values=("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"),
                    width=3, font=("Consolas",8), state="readonly")
                tlc2.pack(side=tk.LEFT, padx=1)
                xv_entry = tk.Entry(cr, textvariable=xv, bg="#1e1e1e", fg="#569cd6",
                         font=("Consolas",9), width=6, relief=tk.FLAT)
                xv_entry.pack(side=tk.LEFT, padx=1)
                def toggle_sw2(*a):
                    swf.pack_forget() if tv.get() != "swipe" else swf.pack(before=xv_entry)
                tv.trace_add("write", toggle_sw2)
                toggle_sw2()
                tk.Entry(cr, textvariable=yv, bg="#1e1e1e", fg="#569cd6",
                         font=("Consolas",9), width=6, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)
                tk.Button(cr, text="LOC",
                          command=lambda xv=xv,yv=yv: self._capture_coordinates(xv,yv),
                          bg="#5a5a00", fg="#ffff00", font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=3
                          ).pack(side=tk.LEFT, padx=2)
                cr.vt = vt
                cr.deleted = False
                def dl(widget=cr):
                    widget.deleted = True
                    try: extra_vars.remove(widget.vt)
                    except: pass
                    widget.destroy()
                # Play button for extra coord
                tk.Button(cr, text="Play",
                          command=lambda xv=xv, yv=yv, tv=tv, dv=dv, lv=lv: (
                    __import__("adb_utils").tap(int(xv.get()), int(yv.get())) if tv.get() != "swipe"
                    else __import__("adb_utils").swipe(int(xv.get()), int(yv.get()),
                        int(xv.get())+(0 if dv.get() in ("up","down") else (200 if dv.get()=="right" else -200)),
                        int(yv.get())+(0 if dv.get() in ("left","right") else (-200 if dv.get()=="up" else 200)),
                        300),
                    self.bot_say(f"Play: {tv.get()} ({xv.get()},{yv.get()})"))[0] if True else None,
                          bg="#0e639c", fg="white",
                          font=("Consolas",8), relief=tk.FLAT, cursor="hand2", width=4
                          ).pack(side=tk.LEFT, padx=1)
                tk.Button(cr, text="X", command=dl, bg="#5a0000", fg="#ff6b6b",
                          font=("Consolas",8), relief=tk.FLAT, cursor="hand2", width=3
                          ).pack(side=tk.LEFT, padx=2)
                return vt
            mxv = tk.StringVar(value=str(coords[0][0]))
            myv = tk.StringVar(value=str(coords[0][1]))
            extra_vars.append((tk.StringVar(value=""), mxv, myv))
            mxv_entry = tk.Entry(row, textvariable=mxv, bg="#2d2d2d", fg="#569cd6",
                     font=("Consolas",9), width=5, relief=tk.FLAT)
            mxv_entry.pack(side=tk.LEFT, padx=1)
            myv_entry = tk.Entry(row, textvariable=myv, bg="#2d2d2d", fg="#569cd6",
                     font=("Consolas",9), width=5, relief=tk.FLAT)
            myv_entry.pack(side=tk.LEFT, padx=1)
            toggle_type()
            tk.Button(row, text="LOC",
                      command=lambda xv=mxv,yv=myv: self._capture_coordinates(xv,yv),
                      bg="#5a5a00", fg="#ffff00", font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=3
                      ).pack(side=tk.LEFT, padx=2)
            def mk_add(cnt, af, evl):
                def _add():
                    if not cnt.winfo_ismapped(): cnt.pack(fill=tk.X, after=af)
                    evl.append(mk_cr(cnt, 0, 0, "lan " + str(len(evl))))
                return _add
            tk.Button(row, text="+", command=mk_add(ec, row, extra_vars),
                      bg="#3c3c3c", fg="#4ec9b0",
                      font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=3
                      ).pack(side=tk.LEFT, padx=3)
            for item in coords[1:]:
                if not ec.winfo_ismapped(): ec.pack(fill=tk.X, after=row)
                _cn = item[2] if len(item)>2 else ""
                _ct = item[4] if len(item)>4 else "tap"
                _cd = item[5] if len(item)>5 else "up"
                _cl = item[6] if len(item)>6 else "400"
                extra_vars.append(mk_cr(ec, item[0], item[1], _cn, _ct, _cd, _cl))
            sv["extra_coords"] = extra_vars
            sv["coords"] = coords
            self._editor_steps = steps
            self._editor_win = win
            self._editor_name = name
            tk.Button(row, text="+", command=lambda idx=i: self._editor_add_step_at(idx),
                      bg="#2d6b2d", fg="white",
                      font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=3
                      ).pack(side=tk.LEFT, padx=2)
            # Play button - test step
            def play_this_step(cur=i, xv=mxv, yv=myv, sv_item=sv):
                from adb_utils import tap as a_tap, swipe as a_swipe
                sx, sy = int(xv.get()), int(yv.get())
                tp = sv_item["type_var"].get()
                if tp == "text":
                    from adb_utils import _adb, tap as a_tap
                    self.bot_say(f"Dang go text...")
                    a_tap(sx, sy)
                    cv = sv_item["clear_var"].get()
                    if cv:
                        for _ in range(30):
                            _adb("shell input keyevent 67")
                    txt = sv_item["text_var"].get()
                    if txt:
                        import subprocess
                        from pathlib import Path
                        import time
                        try:
                            adb = str(Path(__file__).parent / "scrcpy" / "adb.exe")
                            a_tap(sx, sy)
                            time.sleep(0.2)
                            for ch in txt:
                                if ch == ' ':
                                    subprocess.run([adb, "shell", "input", "keyevent", "62"],
                                                 capture_output=True, timeout=5)
                                else:
                                    subprocess.run([adb, "shell", "input", "text", ch],
                                                 capture_output=True, timeout=5)
                                time.sleep(0.05)
                            self.bot_say(f"Play: text ok")
                        except Exception as ex:
                            self.bot_error(f"Text error: {ex}")
                    self.bot_say(f'Play: text "{txt}"')
                    return
                if tp == "swipe":
                    dr = sv_item["dir_var"].get()
                    lk = sv_item["len_var"].get()
                    try:
                        pct = int(lk) * 5 if lk.isdigit() else 25
                        from adb_utils import get_screen_size
                        _, sh = get_screen_size()
                        dist = int(pct * sh / 100)
                    except: dist = 200
                    ex, ey = sx, sy
                    if dr == "up": ey = max(0, sy - dist)
                    elif dr == "down": ey = sy + dist
                    elif dr == "left": ex = max(0, sx - dist)
                    elif dr == "right": ex = sx + dist
                    a_swipe(sx, sy, ex, ey, 300)
                    self.bot_say(f"Play: vuot {dr}")
                else:
                    a_tap(sx, sy)
                    self.bot_say(f"Play: tap ({sx},{sy})")
            tk.Button(row, text="Play", command=play_this_step,
                      bg="#0e639c", fg="white",
                      font=("Consolas",9), relief=tk.FLAT, cursor="hand2", width=3
                      ).pack(side=tk.LEFT, padx=2)
            tk.Button(row, text="X", command=container.destroy,
                      bg="#5a0000", fg="#ff6b6b",
                      font=("Consolas",8), relief=tk.FLAT, cursor="hand2", width=3
                      ).pack(side=tk.LEFT, padx=2)
            sv["container"] = container
            edit_vars.append(sv)

        def _on_mw(e):
            canvas.yview_scroll(int(-1*(e.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mw)
        canvas.bind("<Enter>", lambda e: canvas.focus_set())

        def do_save():
            new_steps = []
            rt = 0.0
            for sv_item in edit_vars:
                if sv_item is None: continue
                if sv_item.get("container") and not sv_item["container"].winfo_exists(): continue
                try: rt += max(0, float(sv_item["ts"].get()))
                except: pass
                label = sv_item["label"].get().strip()
                if not label: continue
                coords_list = []
                for item in sv_item.get("extra_coords", []):
                    try:
                        if len(item) >= 7:
                            nv, xv, yv, frame, tv, dv, lv = item
                            if not frame.winfo_exists() or getattr(frame, 'deleted', False): continue
                        elif len(item) >= 4:
                            nv, xv, yv, frame = item
                            if not frame.winfo_exists() or getattr(frame, 'deleted', False): continue
                        else: nv, xv, yv = item
                        coord = [int(xv.get()), int(yv.get())]
                        cn = nv.get().strip()
                        if cn: coord.append(cn)
                        if len(item) >= 7:
                            coord.append(""); coord.append(tv.get() if tv else "tap")
                            coord.append(dv.get() if dv else "up"); coord.append(lv.get() if lv else "400")
                        coords_list.append(coord)
                    except: pass
                if not coords_list: coords_list = [[0,0]]
                tv2 = sv_item.get("type_var")
                step_type = tv2.get() if tv2 else sv_item["orig"].get("type","tap")
                new_step = {"timestamp": round(rt,2), "type": step_type, "label": label,
                    "coords": coords_list, "x": coords_list[0][0], "y": coords_list[0][1],
                    "image_crop": sv_item["orig"].get("image_crop",""),
                    "screen_w": sv_item["orig"].get("screen_w",720),
                    "screen_h": sv_item["orig"].get("screen_h",1280)}
                if step_type == "swipe":
                    dv2 = sv_item.get("dir_var"); lv2 = sv_item.get("len_var")
                    new_step["direction"] = dv2.get() if dv2 else sv_item["orig"].get("direction","up")
                    new_step["length"] = lv2.get() if lv2 else sv_item["orig"].get("length","5")
                elif step_type == "text":
                    tv = sv_item.get("text_var"); cv = sv_item.get("clear_var")
                    new_step["text_content"] = tv.get() if tv else ""
                    new_step["clear_first"] = cv.get() if cv else False
                new_steps.append(new_step)
            save_macro(name, new_steps)
            self._editor_last_save = list(new_steps)
            self.bot_success("Da luu macro: " + name)
        self._do_save = do_save

        bf = tk.Frame(win, bg="#2d2d2d")
        bf.pack(pady=10)
        tk.Button(bf, text="Luu thay doi", command=do_save,
                  bg="#0e639c", fg="white",
                  font=("Consolas",10,"bold"), relief=tk.FLAT, cursor="hand2", width=18
                  ).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="Dong", command=win.destroy,
                  bg="#5a5a5a", fg="white",
                  font=("Consolas",10), relief=tk.FLAT, cursor="hand2", width=18
                  ).pack(side=tk.LEFT, padx=5)

    def _open_file_manager(self):
        self.bot_say("File manager chua san")

    def _open_dataset_manager(self):
        from macro_manager import DATASET_DIR
        classes = {}
        if DATASET_DIR.exists():
            for d in sorted(DATASET_DIR.iterdir()):
                if d.is_dir():
                    pngs = sorted(d.glob("*.png"))
                    if pngs: classes[d.name] = pngs
        win = tk.Toplevel(self.root)
        win.title("Dataset")
        win.geometry("500x350")
        win.configure(bg="#2d2d2d")
        win.transient(self.root)
        win.grab_set()
        total = sum(len(v) for v in classes.values())
        tk.Label(win, text=f"Dataset: {total} anh, {len(classes)} class",
                 bg="#2d2d2d", fg="#ffffff",
                 font=("Consolas", 12, "bold")).pack(pady=10)
        for cn, imgs in sorted(classes.items()):
            row = tk.Frame(win, bg="#3c3c3c", pady=2)
            row.pack(fill=tk.X, padx=10, pady=1)
            tk.Label(row, text=f"  {cn}: {len(imgs)}", bg=row["bg"], fg="#4ec9b0",
                     font=("Consolas", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(win, text="Dong", command=win.destroy,
                  bg="#5a5a5a", fg="white",
                  font=("Consolas", 10), relief=tk.FLAT, cursor="hand2", width=10).pack(pady=20)

    def run(self):
        self.root.mainloop()

    def quit(self):
        self.root.quit()
