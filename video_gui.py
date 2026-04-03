#!/usr/bin/env python3
"""standalone desktop GUI for QBot video generation."""

import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
import json
import threading
import asyncio
from pathlib import Path

# Important: Must run from the root directory to access core modules
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import (
    VOICES, FONT_PATHS, DATA_DIR, AUDIO_DIR, OUTPUT_DIR,
    VIDEO_TOOL_DEFAULTS, VIDEO_SETTINGS_FILE
)
from core.data import load_quran_data, load_quran_text_simple, get_sura_start_index
from core.audio import gen_mp3
from core.subtitles import get_verse_durations
from core.video import gen_video

QURAN_DATA = load_quran_data(DATA_DIR)
VERSES_SIMPLE = load_quran_text_simple(DATA_DIR)

def get_verses(sura, start, end):
    idx = get_sura_start_index(QURAN_DATA, sura)
    return [VERSES_SIMPLE[idx + aya - 1] for aya in range(start, end + 1)]


class VideoGenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quran Video Generator")
        self.geometry("600x750")
        self.resizable(False, False)

        # Style
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        
        style.configure("Header.TLabel", font=("Helvetica", 11, "bold"))
        style.configure("Status.TLabel", foreground="gray")
        style.configure("Action.TButton", padding=6)
        
        # Variables
        self.sura_names = [f"{i} - {QURAN_DATA['Sura'][i][4]}" for i in range(1, 115)]
        
        # Core vars initialized with hardcoded defaults first
        d = VIDEO_TOOL_DEFAULTS
        self.sura_var = tk.StringVar(value=self.sura_names[d["sura"]-1])
        self.start_aya_var = tk.StringVar(value=str(d["start"]))
        self.end_aya_var = tk.StringVar(value=str(d["end"]))
        self.voice_var = tk.StringVar(value=d["voice"])
        self.font_var = tk.StringVar(value=d["font"])
        self.template_var = tk.StringVar(value=d["template"])
        
        self.text_color_var = tk.StringVar(value=d["text_color"])
        self.border_width_var = tk.StringVar(value=str(d["border_width"]))
        self.border_color_var = tk.StringVar(value=d["border_color"])
        
        self.bg_mode_var = tk.StringVar(value=d["bg_mode"])
        self.bg_color_var = tk.StringVar(value=d["bg_color"])
        self.bg_path_var = tk.StringVar(value=d["bg_path"])
        self.bg_behavior_var = tk.StringVar(value=d["bg_behavior"])
        self.ratio_var = tk.StringVar(value=d["ratio"])
        
        self.out_file_var = tk.StringVar(value="")
        
        # Trace for dynamic range
        self.sura_var.trace_add("write", self._on_sura_change)
        
        # Try to load previous settings
        self.load_settings()
        
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _on_sura_change(self, *args):
        """Update end_aya_var to last ayah when sura changes."""
        try:
            sura_str = self.sura_var.get().split(" - ")[0]
            sura = int(sura_str)
            max_aya = int(QURAN_DATA["Sura"][sura][1])
            self.end_aya_var.set(str(max_aya))
        except: pass

    def load_settings(self):
        """Restore settings from gitignored json file."""
        if not VIDEO_SETTINGS_FILE.exists():
            return
        try:
            with open(VIDEO_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Maps key in json to self.var_var
            mapping = {
                "sura_index": (self.sura_var, lambda x: self.sura_names[x] if x < len(self.sura_names) else self.sura_names[0]),
                "start": (self.start_aya_var, str),
                "end": (self.end_aya_var, str),
                "voice": (self.voice_var, str),
                "font": (self.font_var, str),
                "template": (self.template_var, str),
                "text_color": (self.text_color_var, str),
                "border_width": (self.border_width_var, str),
                "border_color": (self.border_color_var, str),
                "bg_mode": (self.bg_mode_var, str),
                "bg_color": (self.bg_color_var, str),
                "bg_path": (self.bg_path_var, str),
                "bg_behavior": (self.bg_behavior_var, str),
                "ratio": (self.ratio_var, str),
            }
            
            for key, (var, transform) in mapping.items():
                if key in data:
                    try:
                        var.set(transform(data[key]))
                    except: pass
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Persist current settings to json file."""
        try:
            sura_idx = self.sura_names.index(self.sura_var.get())
        except: sura_idx = 0
            
        data = {
            "sura_index": sura_idx,
            "start": self.start_aya_var.get(),
            "end": self.end_aya_var.get(),
            "voice": self.voice_var.get(),
            "font": self.font_var.get(),
            "template": self.template_var.get(),
            "text_color": self.text_color_var.get(),
            "border_width": self.border_width_var.get(),
            "border_color": self.border_color_var.get(),
            "bg_mode": self.bg_mode_var.get(),
            "bg_color": self.bg_color_var.get(),
            "bg_path": self.bg_path_var.get(),
            "bg_behavior": self.bg_behavior_var.get(),
            "ratio": self.ratio_var.get(),
        }
        try:
            with open(VIDEO_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def on_closing(self):
        self.save_settings()
        self.destroy()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tabs
        tab_content = ttk.Frame(notebook)
        tab_style = ttk.Frame(notebook)
        tab_bg = ttk.Frame(notebook)
        
        notebook.add(tab_content, text="Content & Audio")
        notebook.add(tab_style, text="Text Style")
        notebook.add(tab_bg, text="Background")

        self._build_content_tab(tab_content)
        self._build_style_tab(tab_style)
        self._build_bg_tab(tab_bg)

        # Footer Area
        footer = ttk.Frame(self)
        footer.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        btn_out = ttk.Button(footer, text="Select Output File...", command=self.select_output)
        btn_out.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        lbl_out = ttk.Label(footer, textvariable=self.out_file_var, style="Status.TLabel")
        lbl_out.pack(side=tk.TOP, anchor=tk.W)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(footer, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.TOP, fill=tk.X, pady=(10, 5))
        
        self.lbl_status = ttk.Label(footer, text="Ready.")
        self.lbl_status.pack(side=tk.TOP, anchor=tk.W)
        
        action_frame = ttk.Frame(footer)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        btn_reset = ttk.Button(action_frame, text="Reset to Defaults", command=self.reset_defaults)
        btn_reset.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)
        
        self.btn_gen = ttk.Button(action_frame, text="Generate Video", command=self.generate, style="Action.TButton")
        self.btn_gen.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def reset_defaults(self):
        d = VIDEO_TOOL_DEFAULTS
        self.sura_var.set(self.sura_names[d["sura"]-1])
        self.start_aya_var.set(str(d["start"]))
        self.end_aya_var.set(str(d["end"]))
        self.voice_var.set(d["voice"])
        self.font_var.set(d["font"])
        self.template_var.set(d["template"])
        self.text_color_var.set(d["text_color"])
        self.border_width_var.set(str(d["border_width"]))
        self.border_color_var.set(d["border_color"])
        self.bg_mode_var.set(d["bg_mode"])
        self.bg_color_var.set(d["bg_color"])
        self.bg_path_var.set(d["bg_path"])
        self.bg_behavior_var.set(d["bg_behavior"])
        self.ratio_var.set(d["ratio"])
        self.out_file_var.set("")

    def _build_content_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="Quran Selection")
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame, text="Sura:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        cb_sura = ttk.Combobox(frame, textvariable=self.sura_var, values=self.sura_names, state="readonly", width=15)
        cb_sura.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Start Ayah:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Entry(frame, textvariable=self.start_aya_var, width=5).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="End Ayah:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Entry(frame, textvariable=self.end_aya_var, width=5).grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        
        reciter_frame = ttk.LabelFrame(parent, text="Audio & Reciter")
        reciter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(reciter_frame, text="Voice:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        voices = list(VOICES.keys())
        cb = ttk.Combobox(reciter_frame, textvariable=self.voice_var, values=voices, state="readonly", width=35)
        cb.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

    def _build_style_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="Typography")
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(frame, text="Font:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        cb = ttk.Combobox(frame, textvariable=self.font_var, values=list(FONT_PATHS.keys()), state="readonly")
        cb.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Template:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        cb_tmp = ttk.Combobox(frame, textvariable=self.template_var, values=["default", "enhanced"], state="readonly", width=12)
        cb_tmp.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(frame, text="Text Color:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        color_frame = ttk.Frame(frame)
        color_frame.grid(row=1, column=1, sticky=tk.W)
        ttk.Entry(color_frame, textvariable=self.text_color_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(color_frame, text="Pick", command=lambda: self.pick_color(self.text_color_var)).pack(side=tk.LEFT)

        border_frame = ttk.LabelFrame(parent, text="Text Border (Stroke)")
        border_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(border_frame, text="Border Width (px):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Spinbox(border_frame, textvariable=self.border_width_var, from_=0, to=10, width=5).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(border_frame, text="Border Color:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.E)
        bc_frame = ttk.Frame(border_frame)
        bc_frame.grid(row=1, column=1, sticky=tk.W)
        ttk.Entry(bc_frame, textvariable=self.border_color_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bc_frame, text="Pick", command=lambda: self.pick_color(self.border_color_var)).pack(side=tk.LEFT)
        
        ratio_frame = ttk.LabelFrame(parent, text="Dimensions")
        ratio_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(ratio_frame, text="Aspect Ratio:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Combobox(ratio_frame, textvariable=self.ratio_var, values=["portrait", "landscape"], state="readonly").grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

    def _build_bg_tab(self, parent):
        frame = ttk.LabelFrame(parent, text="Background Type")
        frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Radiobutton(frame, text="Solid Color", variable=self.bg_mode_var, value="color").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(frame, text="Single Image", variable=self.bg_mode_var, value="image").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(frame, text="Single Video", variable=self.bg_mode_var, value="video").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Radiobutton(frame, text="Folder (Randomized)", variable=self.bg_mode_var, value="folder").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        
        self.opt_frame = ttk.LabelFrame(parent, text="Background Options")
        self.opt_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Color picker
        self.cf = ttk.Frame(self.opt_frame)
        self.cf.pack(fill=tk.X, pady=2)
        ttk.Label(self.cf, text="Solid Color:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.cf, textvariable=self.bg_color_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.cf, text="Pick", command=lambda: self.pick_color(self.bg_color_var)).pack(side=tk.LEFT)
        
        # File selector
        self.ff = ttk.Frame(self.opt_frame)
        self.ff.pack(fill=tk.X, pady=5)
        ttk.Label(self.ff, text="Path:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(self.ff, textvariable=self.bg_path_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.ff, text="Browse...", command=self.select_bg_path).pack(side=tk.LEFT)
        
        # Behavior
        self.bf = ttk.Frame(self.opt_frame)
        self.bf.pack(fill=tk.X, pady=2)
        ttk.Label(self.bf, text="Behavior (Folder/Images):").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(self.bf, textvariable=self.bg_behavior_var, values=["permanent", "per_verse"], state="readonly").pack(side=tk.LEFT, padx=5)

        self.bg_mode_var.trace_add("write", self._toggle_bg_options)
        self._toggle_bg_options()

    def _toggle_bg_options(self, *args):
        mode = self.bg_mode_var.get()
        if mode == "color":
            self.ff.pack_forget()
            self.bf.pack_forget()
            self.cf.pack(fill=tk.X, pady=2)
        else:
            self.cf.pack_forget()
            self.ff.pack(fill=tk.X, pady=5)
            self.bf.pack(fill=tk.X, pady=2)

    def pick_color(self, str_var):
        color = colorchooser.askcolor(title="Choose color", initialcolor=str_var.get())
        if color[1]:
            str_var.set(color[1])
            
    def select_bg_path(self):
        import subprocess, shutil
        mode = self.bg_mode_var.get()
        has_zenity = shutil.which("zenity") is not None
        
        p = ""
        if mode == "folder":
            if has_zenity:
                res = subprocess.run(["zenity", "--file-selection", "--directory", "--title=Select Background Folder"], capture_output=True, text=True)
                p = res.stdout.strip()
            else:
                p = filedialog.askdirectory()
        else:
            if has_zenity:
                res = subprocess.run(["zenity", "--file-selection", "--title=Select Background Media"], capture_output=True, text=True)
                p = res.stdout.strip()
            else:
                p = filedialog.askopenfilename()
        if p:
            self.bg_path_var.set(p)
            
    def select_output(self):
        f = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if f:
            self.out_file_var.set(f)

    def hex_to_rgba(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (r, g, b, 255)
        return (255, 255, 255, 255) # fallback

    def update_progress(self, pct, msg):
        self.progress_var.set(pct)
        self.lbl_status.config(text=msg)
        self.update_idletasks()

    def generate(self):
        try:
            sura_str = self.sura_var.get().split(" - ")[0]
            sura = int(sura_str)
            start = int(self.start_aya_var.get())
            end = int(self.end_aya_var.get())
        except ValueError:
            messagebox.showerror("Error", "Sura and Ayah must be valid numbers.")
            return
            
        max_aya = int(QURAN_DATA["Sura"][sura][1])
        if start < 1 or end > max_aya or start > end:
            messagebox.showerror("Error", f"Invalid Ayah range. Sura {sura} has {max_aya} Ayahs.")
            return

        voice = self.voice_var.get()
        
        if not self.out_file_var.get():
            auto_name = f"quran_{sura:03d}_{start:03d}_{end:03d}_{voice}.mp4"
            out_path = OUTPUT_DIR / "local"
            out_path.mkdir(exist_ok=True, parents=True)
            self.out_file_var.set(str(out_path / auto_name))

        self.btn_gen.config(state=tk.DISABLED)
        self.lbl_status.config(text="Preparing...")
        
        # Run async generation in a background thread to keep GUI responsive
        def _run_gen():
            asyncio.run(self._gen_async(sura, start, end, voice))
            
        threading.Thread(target=_run_gen, daemon=True).start()

    async def _gen_async(self, sura, start, end, voice):
        try:
            verses = get_verses(sura, start, end)
            if not verses:
                raise ValueError("Could not find verses for the given range.")
            
            self.update_progress(5, "Downloading audio and extracting alignments...")
            
            out_file = Path(self.out_file_var.get())
            out_dir = out_file.parent
            
            audio_path = gen_mp3(
                audio_dir=AUDIO_DIR,
                output_dir=out_dir,
                quran_data=QURAN_DATA,
                voice=voice,
                start_sura=sura,
                start_aya=start,
                end_sura=sura,
                end_aya=end,
                progress_cb=lambda pct: self.update_progress(pct, "Processing audio...")
            )
            
            alignments = get_verse_durations(AUDIO_DIR, voice, sura, start, end)
            
            if not alignments or len(alignments) < len(verses):
                # Fallback if alignment is missing
                alignments = [3.0] * len(verses)

            tc = self.hex_to_rgba(self.text_color_var.get())
            bc = self.hex_to_rgba(self.border_color_var.get())
            bw = int(self.border_width_var.get())
            
            # Instead of returning a path like the bot does, we can move the cached result
            cache_path = gen_video(
                verses_list=verses,
                start_aya=start,
                sura=sura,
                voice=voice,
                audio_path=audio_path,
                output_dir=out_file.parent,
                ratio=self.ratio_var.get(),
                bg_mode=self.bg_mode_var.get(),
                bg_path=self.bg_path_var.get() if self.bg_mode_var.get() != "color" else self.bg_color_var.get(),
                bg_behavior=self.bg_behavior_var.get(),
                font_key=self.font_var.get(),
                text_color=tc,
                stroke_width=bw,
                stroke_color=bc,
                template=self.template_var.get(),
                verse_durations=alignments,
                progress_cb=self.update_progress
            )
            
            # if cache_path != out_file:
            #     import shutil
            #     shutil.copy2(cache_path, out_file)
            out_file = cache_path
            
            self.update_progress(100, "Done! Video saved.")
            messagebox.showinfo("Success", f"Video exported to:\n{out_file}")
            
        except Exception as e:
            self.update_progress(0, f"Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.btn_gen.config(state=tk.NORMAL)

if __name__ == "__main__":
    app = VideoGenApp()
    app.mainloop()
