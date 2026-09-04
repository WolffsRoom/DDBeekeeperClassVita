import os
import sys
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

if getattr(sys, "frozen", False):
    APP_ROOT = Path(sys.executable).resolve().parent
    BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
else:
    APP_ROOT = Path(__file__).resolve().parents[1]
    BUNDLE_ROOT = APP_ROOT

PATCHER_DIR = BUNDLE_ROOT / "patcher"
if str(PATCHER_DIR) not in sys.path:
    sys.path.insert(0, str(PATCHER_DIR))

import dd_beekeeper_vita_patcher as patcher

BG = "#111315"
PANEL = "#191c1f"
PANEL_2 = "#202429"
ENTRY = "#0d0f11"
TEXT = "#ececec"
MUTED = "#a9adb3"
ACCENT = "#d8b36a"
ACCENT_HOVER = "#e7c782"
BORDER = "#2d3238"
GOOD = "#78c091"
ERROR = "#d97f7f"

class TextRedirector:
    def __init__(self, app): self.app = app
    def write(self, data):
        if data: self.app.after(0, lambda d=data: self.app.append_log(d))
    def flush(self): pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DD Beekeeper Class Vita Patcher")
        self.geometry("920x690")
        self.minsize(820, 620)
        self.configure(bg=BG)
        try:
            icon_path = BUNDLE_ROOT / "assets" / "image.ico"
            if icon_path.exists(): self.iconbitmap(default=str(icon_path))
        except Exception:
            pass

        self.psarc = tk.StringVar()
        self.mod = tk.StringVar()
        self.audio = tk.StringVar()
        self.output = tk.StringVar(value=str(APP_ROOT / "output"))
        self.force = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready")

        self._build_ui()

    def _label(self, parent, text, size=10, bold=False, fg=TEXT, **kw):
        return tk.Label(parent, text=text, bg=parent.cget("bg"), fg=fg,
                        font=("Segoe UI", size, "bold" if bold else "normal"), **kw)

    def _button(self, parent, text, command, primary=False, width=None):
        bg = ACCENT if primary else PANEL_2
        fg = "#111315" if primary else TEXT
        active_bg = ACCENT_HOVER if primary else "#2a3036"
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         activebackground=active_bg, activeforeground=fg,
                         relief="flat", bd=0, padx=16, pady=9, cursor="hand2",
                         font=("Segoe UI", 10, "bold" if primary else "normal"),
                         width=width)

    def _path_row(self, parent, label, var, browse_cmd, optional=False):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=(0, 10))
        title = label + ("  (optional)" if optional else "")
        self._label(row, title, size=9, bold=True, fg=TEXT).pack(anchor="w", pady=(0, 5))
        line = tk.Frame(row, bg=PANEL)
        line.pack(fill="x")
        entry = tk.Entry(line, textvariable=var, bg=ENTRY, fg=TEXT,
                         insertbackground=TEXT, relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT, font=("Segoe UI", 10))
        entry.pack(side="left", fill="x", expand=True, ipady=8)
        self._button(line, "Browse", browse_cmd).pack(side="left", padx=(8, 0))

    def _build_ui(self):
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        canvas = tk.Canvas(shell, bg=BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        page = tk.Frame(canvas, bg=BG)
        page_id = canvas.create_window((0, 0), window=page, anchor="nw")
        page.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(page_id, width=e.width))
        def _wheel(event):
            if event.delta:
                canvas.yview_scroll(-1 * int(event.delta / 120) * 3, "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        header = tk.Frame(page, bg=BG)
        header.pack(fill="x", padx=28, pady=(16, 12))
        logo_path = BUNDLE_ROOT / "assets" / "darkest_dungeon_logo.png"
        self.logo_image = None
        if logo_path.exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(logo_path).convert("RGBA")
                max_width = 300
                if img.width > max_width:
                    ratio = max_width / img.width
                    img = img.resize((max_width, max(1, round(img.height * ratio))), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
                tk.Label(header, image=self.logo_image, bg=BG, bd=0).pack(anchor="center", pady=(0, 4))
            except Exception:
                self._label(header, "Darkest Dungeon", size=20, bold=True, fg=TEXT).pack(anchor="center")
        self._label(header, "PS Vita Edition Patcher", size=11, bold=True, fg=MUTED).pack(anchor="center", pady=(1, 2))
        self._label(header, "By WolffsRooom", size=9, bold=True, fg=ACCENT).pack(anchor="center", pady=(0, 8))
        self._label(header, "Builds a rePatch package from files you provide. No game, mod, or Sony SDK files are included.", size=9, fg=MUTED).pack(anchor="center")

        body = tk.Frame(page, bg=BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 16))
        inputs = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        inputs.pack(fill="x")
        inner = tk.Frame(inputs, bg=PANEL)
        inner.pack(fill="x", padx=18, pady=16)
        self._label(inner, "Source files", size=11, bold=True).pack(anchor="w", pady=(0, 12))
        self._path_row(inner, "Vita content_patch_13.psarc", self.psarc, self.pick_psarc)
        self._path_row(inner, "Original Beekeeper mod (.zip or folder)", self.mod, self.pick_mod)
        self._path_row(inner, "Original audio/load_order.json", self.audio, self.pick_audio, optional=True)
        self._path_row(inner, "Output folder", self.output, self.pick_output)

        options = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        options.pack(fill="x", pady=(12, 0))
        oin = tk.Frame(options, bg=PANEL)
        oin.pack(fill="x", padx=18, pady=14)
        self._label(oin, "Options", size=11, bold=True).pack(anchor="w", pady=(0, 8))
        cb = tk.Checkbutton(oin, text="Force Beekeeper in Stage Coach — debug/test only", variable=self.force, bg=PANEL, fg=TEXT, activebackground=PANEL, activeforeground=TEXT, selectcolor=ENTRY, highlightthickness=0, font=("Segoe UI", 10), cursor="hand2")
        cb.pack(anchor="w")
        self._label(oin, "Disabled by default. Leave this off for a normal gameplay build.", size=9, fg=MUTED).pack(anchor="w", padx=(24, 0), pady=(3, 0))

        actions = tk.Frame(body, bg=BG)
        actions.pack(fill="x", pady=(14, 10))
        self.runbtn = self._button(actions, "Build rePatch", self.start, primary=True, width=16)
        self.runbtn.pack(side="left")
        self._button(actions, "Open output", self.open_output).pack(side="left", padx=(8, 0))
        status_wrap = tk.Frame(actions, bg=BG)
        status_wrap.pack(side="right")
        self._label(status_wrap, "Status:", size=9, fg=MUTED).pack(side="left")
        self.status_label = self._label(status_wrap, "", size=9, bold=True, fg=GOOD)
        self.status_label.configure(textvariable=self.status)
        self.status_label.pack(side="left", padx=(5, 0))

        log_card = tk.Frame(body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        log_card.pack(fill="both", expand=True)
        top = tk.Frame(log_card, bg=PANEL)
        top.pack(fill="x", padx=14, pady=(10, 6))
        self._label(top, "Build log", size=10, bold=True).pack(side="left")
        self._button(top, "Clear", self.clear_log).pack(side="right")
        self.log = tk.Text(log_card, bg=ENTRY, fg="#d7d7d7", insertbackground=TEXT, relief="flat", bd=0, wrap="word", font=("Cascadia Mono", 9), padx=10, pady=10, state="disabled", height=12)
        self.log.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        footer = tk.Frame(page, bg=BG)
        footer.pack(fill="x", padx=28, pady=(0, 14))
        self._label(footer, "DDBeekeeperClassVita", size=9, fg=MUTED).pack(side="left")
        self._label(footer, "By WolffsRooom", size=9, bold=True, fg=ACCENT).pack(side="right")


    def pick_psarc(self):
        p = filedialog.askopenfilename(filetypes=[("PSARC", "*.psarc"), ("All files", "*.*")])
        if p: self.psarc.set(p)

    def pick_mod(self):
        p = filedialog.askopenfilename(filetypes=[("ZIP", "*.zip"), ("All files", "*.*")])
        if p:
            self.mod.set(p); return
        p = filedialog.askdirectory()
        if p: self.mod.set(p)

    def pick_audio(self):
        p = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if p: self.audio.set(p)

    def pick_output(self):
        p = filedialog.askdirectory()
        if p: self.output.set(p)

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def open_output(self):
        p = Path(self.output.get())
        p.mkdir(parents=True, exist_ok=True)
        os.startfile(p)

    def set_status(self, text, color):
        self.status.set(text)
        self.status_label.configure(fg=color)

    def start(self):
        if not self.psarc.get() or not self.mod.get():
            messagebox.showerror("Missing input", "Select the Vita PSARC and the original Beekeeper mod.")
            return
        self.runbtn.configure(state="disabled")
        self.set_status("Building...", ACCENT)
        self.append_log("\n=== DD Beekeeper Class Vita Patcher ===\n")
        threading.Thread(target=self.worker, daemon=True).start()

    def worker(self):
        args = [
            "--psarc", self.psarc.get(),
            "--mod", self.mod.get(),
            "--tools", str(APP_ROOT / "tools"),
            "--output", self.output.get(),
        ]
        if self.audio.get(): args += ["--audio-load-order", self.audio.get()]
        if self.force.get(): args += ["--force-stagecoach"]

        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = TextRedirector(self)
        sys.stderr = TextRedirector(self)
        try:
            patcher.main(args)
            self.after(0, lambda: self.set_status("Completed", GOOD))
            self.after(0, lambda: messagebox.showinfo("Build complete", "rePatch package created and verified successfully."))
        except SystemExit as e:
            self.after(0, lambda: self.set_status("Failed", ERROR))
            self.after(0, lambda: messagebox.showerror("Build failed", str(e)))
        except Exception as e:
            traceback.print_exc()
            self.after(0, lambda: self.set_status("Failed", ERROR))
            self.after(0, lambda msg=str(e): messagebox.showerror("Build failed", msg))
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self.after(0, lambda: self.runbtn.configure(state="normal"))

if __name__ == "__main__":
    App().mainloop()
