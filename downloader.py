"""
GrabIt — Universal Video & Audio Downloader
Supports YouTube, TikTok, Instagram, Twitter/X, Facebook,
Reddit, Twitch, SoundCloud, Vimeo, and 1000+ more sites
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import subprocess
import shutil
import re

# ── Auto-install yt-dlp if missing ──
try:
    import yt_dlp
except ImportError:
    print("[!] Installing yt-dlp...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"])
    import yt_dlp

# ── Auto-install imageio-ffmpeg if missing ──
try:
    import imageio_ffmpeg
except ImportError:
    print("[!] Installing imageio-ffmpeg...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg", "-q"])
    import imageio_ffmpeg

# ── Locate ffmpeg and copy next to script so yt-dlp always finds it ──
FFMPEG_PATH = None

def _setup_ffmpeg():
    global FFMPEG_PATH
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exe_name   = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    target     = os.path.join(script_dir, exe_name)

    if os.path.isfile(target):
        FFMPEG_PATH = target
        print(f"[OK] ffmpeg ready: {target}")
        return

    try:
        src = imageio_ffmpeg.get_ffmpeg_exe()
        if src and os.path.isfile(src):
            shutil.copy2(src, target)
            if sys.platform != "win32":
                os.chmod(target, 0o755)
            FFMPEG_PATH = target
            print(f"[OK] ffmpeg copied: {target}")
            return
    except Exception as e:
        print(f"[!] imageio-ffmpeg error: {e}")

    sys_ff = shutil.which("ffmpeg")
    if sys_ff:
        FFMPEG_PATH = sys_ff
        print(f"[OK] ffmpeg (system): {sys_ff}")
        return

    print("[!] ffmpeg not found — merging/MP3 may not work")

_setup_ffmpeg()


# ─────────────────────────────────────────────────────────────
#  COLORS / FONTS
# ─────────────────────────────────────────────────────────────
DARK_BG    = "#0d0d14"
SURFACE    = "#17171f"
SURFACE2   = "#21212e"
ACCENT     = "#7c6fff"
ACCENT2    = "#a78bfa"
GREEN      = "#4ade80"
RED        = "#f87171"
TEXT       = "#f0f0ff"
TEXT_MUTED = "#6b7280"
BORDER     = "#2a2a3a"

FONT_HEADING = ("Segoe UI", 13, "bold")
FONT_BODY    = ("Segoe UI", 11)
FONT_SMALL   = ("Segoe UI", 9)
FONT_MONO    = ("Consolas", 10)

SUPPORTED_SITES = [
    "YouTube", "TikTok", "Instagram", "Twitter/X", "Facebook",
    "Reddit", "Twitch", "SoundCloud", "Vimeo", "Dailymotion",
    "Bilibili", "Pinterest", "LinkedIn", "and 1000+ more..."
]


# ─────────────────────────────────────────────────────────────
#  DOWNLOADER LOGIC
# ─────────────────────────────────────────────────────────────
class Downloader:
    def __init__(self):
        self.cancelled = False

    def get_info(self, url):
        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        if FFMPEG_PATH:
            opts["ffmpeg_location"] = FFMPEG_PATH
            
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    def download(self, url, output_dir, mode, quality, audio_quality,
                 progress_hook, done_hook, error_hook):
        self.cancelled = False

        if mode == "audio":
            fmt      = "bestaudio/best"
            postproc = [{"key": "FFmpegExtractAudio",
                          "preferredcodec": "mp3", 
                          "preferredquality": audio_quality}]
        else:
            # Force mp4 and m4a explicitly to ensure ffmpeg doesn't fail the merge
            v_qual = "" if quality == "best" else f"[height<={quality}]"
            fmt = f"bestvideo{v_qual}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{v_qual}+bestaudio/best{v_qual}/best"
            postproc = []

        outtmpl = os.path.join(output_dir, "%(title).60s.%(ext)s")
        opts = {
            "format":              fmt,
            "outtmpl":             outtmpl,
            "progress_hooks":      [progress_hook],
            "postprocessors":      postproc,
            "noplaylist":          True,
            "merge_output_format": "mp4",
            "quiet":               True,
            "no_warnings":         True,
        }
        if FFMPEG_PATH:
            opts["ffmpeg_location"] = FFMPEG_PATH

        def run():
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                if not self.cancelled:
                    done_hook()
            except yt_dlp.utils.DownloadError as e:
                if not self.cancelled:
                    error_hook(str(e))
            except Exception as e:
                if not self.cancelled:
                    error_hook(str(e))

        threading.Thread(target=run, daemon=True).start()

    def cancel(self):
        self.cancelled = True


# ─────────────────────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GrabIt — Universal Downloader")
        self.geometry("760x620")
        self.minsize(680, 560)
        self.configure(bg=DARK_BG)
        self.resizable(True, True)

        self.dl             = Downloader()
        self.output_dir     = os.path.join(os.path.expanduser("~"), "Downloads")
        self.is_downloading = False

        self._build_ui()
        self._setup_styles()

    # ── STYLES ───────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TProgressbar",
                     troughcolor=SURFACE2, background=ACCENT,
                     bordercolor=SURFACE2, lightcolor=ACCENT2,
                     darkcolor=ACCENT, thickness=8)
        s.configure("TNotebook", background=DARK_BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=SURFACE2, foreground=TEXT_MUTED,
                     padding=[16, 8], font=FONT_BODY)
        s.map("TNotebook.Tab",
              background=[("selected", SURFACE)],
              foreground=[("selected", TEXT)])
        s.configure("Treeview", background=SURFACE2, foreground=TEXT,
                     fieldbackground=SURFACE2, borderwidth=0,
                     font=FONT_BODY, rowheight=28)
        s.configure("Treeview.Heading", background=SURFACE, foreground=TEXT_MUTED,
                     font=FONT_SMALL, borderwidth=0)
        s.map("Treeview", background=[("selected", ACCENT)])

    # ── MAIN LAYOUT ──────────────────────────────────────────
    def _build_ui(self):
        # Header bar
        hdr = tk.Frame(self, bg=SURFACE, height=70)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡ GrabIt", font=("Segoe UI", 20, "bold"),
                 bg=SURFACE, fg=ACCENT).pack(side="left", padx=20, pady=16)
        tk.Label(hdr, text="Universal Video & Audio Downloader",
                 font=FONT_BODY, bg=SURFACE, fg=TEXT_MUTED).pack(side="left", pady=16)
        tk.Label(hdr, text="  ·  ".join(SUPPORTED_SITES[:6]) + "  ·  ...",
                 font=FONT_SMALL, bg=SURFACE, fg=TEXT_MUTED).pack(side="right", padx=20)

        # Tabs
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.nb = nb

        tab_dl    = tk.Frame(nb, bg=DARK_BG)
        tab_hist  = tk.Frame(nb, bg=DARK_BG)
        tab_about = tk.Frame(nb, bg=DARK_BG)
        nb.add(tab_dl,    text="  ⬇  Download  ")
        nb.add(tab_hist,  text="  📋  History  ")
        nb.add(tab_about, text="  ℹ  About  ")

        self._build_download_tab(tab_dl)
        self._build_history_tab(tab_hist)
        self._build_about_tab(tab_about)

    # ── DOWNLOAD TAB ─────────────────────────────────────────
    def _build_download_tab(self, parent):
        # URL input
        url_card = tk.Frame(parent, bg=SURFACE)
        url_card.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(url_card, text="Paste URL", font=FONT_HEADING,
                 bg=SURFACE, fg=TEXT).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(url_card,
                 text="YouTube · TikTok · Instagram · Twitter/X · Facebook · Reddit · Vimeo · SoundCloud...",
                 font=FONT_SMALL, bg=SURFACE, fg=TEXT_MUTED).pack(anchor="w", padx=16, pady=(0, 8))

        url_row = tk.Frame(url_card, bg=SURFACE)
        url_row.pack(fill="x", padx=16, pady=(0, 14))
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            url_row, textvariable=self.url_var, font=FONT_BODY,
            bg=SURFACE2, fg=TEXT, insertbackground=TEXT, relief="flat",
            bd=0, highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=10, ipadx=12)
        self.url_entry.bind("<Return>", lambda e: self._fetch_info())

        self._btn(url_row, "📋 Paste", self._paste_url,
                  bg=SURFACE2, fg=TEXT_MUTED).pack(side="left", padx=(8, 0))
        self.btn_fetch = self._btn(url_row, "🔍 Fetch Info", self._fetch_info,
                                    bg=ACCENT, fg="white")
        self.btn_fetch.pack(side="left", padx=(8, 0))

        # Info card (hidden by default)
        self.info_card      = tk.Frame(parent, bg=SURFACE2)
        self.info_title_var = tk.StringVar()
        self.info_meta_var  = tk.StringVar()
        tk.Label(self.info_card, textvariable=self.info_title_var,
                 font=FONT_HEADING, bg=SURFACE2, fg=TEXT,
                 wraplength=680, justify="left").pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(self.info_card, textvariable=self.info_meta_var,
                 font=FONT_SMALL, bg=SURFACE2, fg=TEXT_MUTED).pack(anchor="w", padx=16, pady=(0, 10))

        # Options row
        opts_card = tk.Frame(parent, bg=SURFACE)
        opts_card.pack(fill="x", padx=20, pady=(0, 10))

        # Mode
        mf = tk.Frame(opts_card, bg=SURFACE)
        mf.pack(side="left", padx=16, pady=12)
        tk.Label(mf, text="Mode", font=FONT_SMALL, bg=SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        self.mode_var = tk.StringVar(value="video")
        mr = tk.Frame(mf, bg=SURFACE)
        mr.pack(anchor="w", pady=(4, 0))
        for lbl, val in [("🎬 Video", "video"), ("🎵 Audio MP3", "audio")]:
            tk.Radiobutton(mr, text=lbl, variable=self.mode_var, value=val,
                           bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
                           activebackground=SURFACE, activeforeground=TEXT,
                           font=FONT_BODY, cursor="hand2",
                           command=self._on_mode_change).pack(side="left", padx=(0, 16))

        # Quality Dynamic Frame
        self.qual_frame = tk.Frame(opts_card, bg=SURFACE)
        self.qual_frame.pack(side="left", padx=16, pady=12)
        tk.Label(self.qual_frame, text="Quality / Bitrate", font=FONT_SMALL,
                 bg=SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        
        self.qr_container = tk.Frame(self.qual_frame, bg=SURFACE)
        self.qr_container.pack(anchor="w", pady=(4, 0))

        self.qual_var       = tk.StringVar(value="best")
        self.audio_qual_var = tk.StringVar(value="320")

        # Video Options Frame
        self.frame_vid_qual = tk.Frame(self.qr_container, bg=SURFACE)
        for lbl, val in [("Best", "best"), ("1080p", "1080"), ("720p", "720"), ("480p", "480")]:
            tk.Radiobutton(self.frame_vid_qual, text=lbl, variable=self.qual_var, value=val,
                           bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
                           activebackground=SURFACE, activeforeground=TEXT,
                           font=FONT_BODY, cursor="hand2").pack(side="left", padx=(0, 12))
                           
        # Audio Options Frame
        self.frame_aud_qual = tk.Frame(self.qr_container, bg=SURFACE)
        for lbl, val in [("320 kbps", "320"), ("192 kbps", "192"), ("128 kbps", "128")]:
            tk.Radiobutton(self.frame_aud_qual, text=lbl, variable=self.audio_qual_var, value=val,
                           bg=SURFACE, fg=TEXT, selectcolor=SURFACE2,
                           activebackground=SURFACE, activeforeground=TEXT,
                           font=FONT_BODY, cursor="hand2").pack(side="left", padx=(0, 12))

        # Show Video options by default
        self.frame_vid_qual.pack(fill="both", expand=True)

        # Save folder
        df = tk.Frame(opts_card, bg=SURFACE)
        df.pack(side="right", padx=16, pady=12)
        tk.Label(df, text="Save to", font=FONT_SMALL, bg=SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        dr = tk.Frame(df, bg=SURFACE)
        dr.pack(anchor="w", pady=(4, 0))
        self.dir_label = tk.Label(dr, text=self._short_path(self.output_dir),
                                   font=FONT_SMALL, bg=SURFACE2, fg=TEXT,
                                   padx=8, pady=4, cursor="hand2")
        self.dir_label.pack(side="left")
        self.dir_label.bind("<Button-1>", lambda e: self._choose_dir())
        self._btn(dr, "📁 Change", self._choose_dir,
                  bg=SURFACE2, fg=TEXT_MUTED).pack(side="left", padx=(6, 0))

        # Download / cancel row
        dl_row = tk.Frame(parent, bg=DARK_BG)
        dl_row.pack(fill="x", padx=20, pady=(0, 10))
        self.btn_download = self._btn(dl_row, "⬇  Download", self._start_download,
                                       bg=ACCENT, fg="white",
                                       font=("Segoe UI", 13, "bold"))
        self.btn_download.pack(side="left")
        self.btn_cancel = self._btn(dl_row, "✕ Cancel", self._cancel,
                                     bg=SURFACE2, fg=RED)
        self.btn_cancel.pack(side="left", padx=(10, 0))
        self.btn_cancel.config(state="disabled")
        self.status_var = tk.StringVar(value="Ready. Paste a URL and press Download.")
        tk.Label(dl_row, textvariable=self.status_var, font=FONT_SMALL,
                 bg=DARK_BG, fg=TEXT_MUTED).pack(side="left", padx=(16, 0))

        # Progress bar
        prog_card = tk.Frame(parent, bg=SURFACE)
        prog_card.pack(fill="x", padx=20, pady=(0, 10))
        self.prog_var = tk.DoubleVar(value=0)
        ttk.Progressbar(prog_card, variable=self.prog_var,
                         maximum=100).pack(fill="x", padx=16, pady=(12, 4))
        pi = tk.Frame(prog_card, bg=SURFACE)
        pi.pack(fill="x", padx=16, pady=(0, 12))
        self.prog_pct_var  = tk.StringVar(value="0%")
        self.prog_size_var = tk.StringVar(value="")
        self.prog_spd_var  = tk.StringVar(value="")
        self.prog_eta_var  = tk.StringVar(value="")
        for var, col in [(self.prog_pct_var, TEXT), (self.prog_size_var, TEXT_MUTED),
                          (self.prog_spd_var, ACCENT2), (self.prog_eta_var, TEXT_MUTED)]:
            tk.Label(pi, textvariable=var, font=FONT_SMALL,
                     bg=SURFACE, fg=col).pack(side="left", padx=(0, 16))

        # Log console
        log_frame = tk.Frame(parent, bg=SURFACE)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        tk.Label(log_frame, text="Log", font=FONT_SMALL,
                 bg=SURFACE, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(8, 2))
        log_inner = tk.Frame(log_frame, bg=SURFACE2)
        log_inner.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.log_text = tk.Text(
            log_inner, bg=SURFACE2, fg=TEXT_MUTED, font=FONT_MONO,
            relief="flat", state="disabled", height=6,
            insertbackground=TEXT, selectbackground=ACCENT,
            wrap="word", cursor="arrow")
        sb = tk.Scrollbar(log_inner, command=self.log_text.yview,
                           bg=SURFACE2, troughcolor=SURFACE2, bd=0)
        self.log_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

        self._log("GrabIt ready. Supports YouTube, TikTok, Instagram, Twitter/X, "
                  "Facebook, Reddit, SoundCloud, Vimeo and 1000+ more sites.")
        self._log("Tip: You can also download audio-only as MP3 using the Audio mode.")
        if FFMPEG_PATH:
            self._log(f"OK ffmpeg ready at: {FFMPEG_PATH}")
        else:
            self._log("WARNING: ffmpeg not found — HD merging and MP3 may not work.")

    # ── HISTORY TAB ──────────────────────────────────────────
    def _build_history_tab(self, parent):
        tk.Label(parent, text="Download History", font=FONT_HEADING,
                 bg=DARK_BG, fg=TEXT).pack(anchor="w", padx=20, pady=(16, 4))
        frame = tk.Frame(parent, bg=SURFACE2)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        cols = ("Time", "Title", "Mode", "Status")
        self.hist_tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
        for col, w, anchor in [("Time", 90, "w"), ("Title", 360, "w"),
                                 ("Mode", 80, "center"), ("Status", 80, "center")]:
            self.hist_tree.heading(col, text=col)
            self.hist_tree.column(col, width=w, anchor=anchor)
        sb2 = ttk.Scrollbar(frame, orient="vertical", command=self.hist_tree.yview)
        self.hist_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.hist_tree.pack(fill="both", expand=True)
        self._btn(parent, "🗑  Clear History", self._clear_history,
                  bg=SURFACE, fg=RED).pack(anchor="w", padx=20, pady=(0, 16))

    # ── ABOUT TAB ────────────────────────────────────────────
    def _build_about_tab(self, parent):
        tk.Label(parent, text="⚡ GrabIt", font=("Segoe UI", 28, "bold"),
                 bg=DARK_BG, fg=ACCENT).pack(pady=(30, 4))
        tk.Label(parent, text="Universal Video & Audio Downloader",
                 font=FONT_HEADING, bg=DARK_BG, fg=TEXT).pack()
        tk.Label(parent, text="Built with Python + yt-dlp · by Ayman",
                 font=FONT_BODY, bg=DARK_BG, fg=TEXT_MUTED).pack(pady=(4, 24))
        tk.Label(parent, text="Supported Sites", font=FONT_HEADING,
                 bg=DARK_BG, fg=TEXT).pack()
        sites = [
            "🎥 YouTube", "🎵 SoundCloud", "📸 Instagram", "🐦 Twitter/X",
            "🎤 TikTok",  "🎬 Vimeo",     "📺 Twitch",    "🌐 Facebook",
            "💬 Reddit",  "📹 Dailymotion","🎞 Bilibili",  "📌 Pinterest",
            "🎙 Mixcloud","📻 BandCamp",  "🏟 ESPN",       "🎮 YouTube Gaming",
        ]
        grid = tk.Frame(parent, bg=DARK_BG)
        grid.pack(pady=12)
        for i, site in enumerate(sites):
            tk.Label(grid, text=site, font=FONT_BODY, bg=SURFACE, fg=TEXT,
                     padx=12, pady=6).grid(row=i // 4, column=i % 4,
                                            padx=4, pady=3, sticky="ew")
        tk.Label(parent, text="+ 1000 more supported by yt-dlp",
                 font=FONT_SMALL, bg=DARK_BG, fg=TEXT_MUTED).pack(pady=(8, 16))
        tk.Label(parent, text="How to use", font=FONT_HEADING, bg=DARK_BG, fg=TEXT).pack()
        for step in ["1. Copy a video/audio URL from any supported site",
                      "2. Paste it into the URL field",
                      "3. Choose Video or Audio MP3 mode",
                      "4. Pick a quality (for video)",
                      "5. Choose your save folder",
                      "6. Hit Download — that's it!"]:
            tk.Label(parent, text=step, font=FONT_BODY,
                     bg=DARK_BG, fg=TEXT_MUTED).pack(anchor="w", padx=120)

    # ── HELPERS ──────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg=SURFACE2, fg=TEXT, font=FONT_BODY):
        return tk.Button(
            parent, text=text, command=cmd, bg=bg, fg=fg,
            activebackground=ACCENT, activeforeground="white",
            relief="flat", bd=0, padx=12, pady=8, font=font, cursor="hand2")

    def _short_path(self, path):
        home = os.path.expanduser("~")
        p = ("~" + path[len(home):]) if path.startswith(home) else path
        return (p[:40] + "...") if len(p) > 40 else p

    def _log(self, msg):
        self.log_text.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {msg}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ── URL ACTIONS ──────────────────────────────────────────
    def _paste_url(self):
        try:
            self.url_var.set(self.clipboard_get().strip())
            self._log(f"Pasted: {self.url_var.get()[:80]}")
        except Exception:
            pass

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.output_dir,
                                     title="Choose download folder")
        if d:
            self.output_dir = d
            self.dir_label.config(text=self._short_path(d))
            self._log(f"Save folder: {d}")

    def _on_mode_change(self):
        # Swap between Video Qualities and Audio Qualities based on mode
        mode = self.mode_var.get()
        if mode == "audio":
            self.frame_vid_qual.pack_forget()
            self.frame_aud_qual.pack(fill="both", expand=True)
        else:
            self.frame_aud_qual.pack_forget()
            self.frame_vid_qual.pack(fill="both", expand=True)

    def _fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a URL first.")
            return
        self.status_var.set("Fetching info...")
        self._log(f"Fetching info for: {url[:80]}")
        self.btn_fetch.config(state="disabled", text="⏳ Fetching...")

        def run():
            try:
                info       = self.dl.get_info(url)
                title      = info.get("title", "Unknown")
                uploader   = info.get("uploader", info.get("channel", ""))
                duration   = info.get("duration", 0)
                view_count = info.get("view_count", 0)
                extractor  = info.get("extractor_key", "")
                dur_str    = (f"{int(duration // 60)}:{int(duration % 60):02d}"
                               if duration else "?")
                views_str  = f"{view_count:,}" if view_count else "?"
                self.after(0, lambda: self._on_info_fetched(
                    title, uploader, dur_str, views_str, extractor))
            except Exception as e:
                self.after(0, lambda: self._on_info_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_info_fetched(self, title, uploader, duration, views, extractor):
        self.info_title_var.set(f"📄 {title[:80]}")
        self.info_meta_var.set(
            f"{extractor}  ·  {uploader}  ·  {duration}  ·  {views} views")
        self.info_card.pack(fill="x", padx=20, pady=(0, 6))
        self.btn_fetch.config(state="normal", text="🔍 Fetch Info")
        self.status_var.set("Ready to download.")
        self._log(f"Found: {title[:60]} ({duration})")

    def _on_info_error(self, err):
        self.btn_fetch.config(state="normal", text="🔍 Fetch Info")
        self.status_var.set("Could not fetch info.")
        self._log(f"Error: {err[:120]}")

    # ── DOWNLOAD ─────────────────────────────────────────────
    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a URL first.")
            return
        if self.is_downloading:
            return
        if not os.path.isdir(self.output_dir):
            messagebox.showerror("Invalid folder",
                                  f"Folder not found:\n{self.output_dir}")
            return

        self.is_downloading = True
        self.prog_var.set(0)
        self.prog_pct_var.set("0%")
        self.prog_size_var.set("")
        self.prog_spd_var.set("")
        self.prog_eta_var.set("")
        self.btn_download.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.status_var.set("Downloading...")
        self._log(f"Starting download: {url[:80]}")
        
        mode_val = self.mode_var.get()
        qual_log = self.audio_qual_var.get() + " kbps" if mode_val == "audio" else self.qual_var.get()
        
        self._log(f"Mode: {mode_val.upper()}  "
                  f"Quality: {qual_log}  "
                  f"Folder: {self.output_dir}")

        self.dl.download(
            url=url,
            output_dir=self.output_dir,
            mode=mode_val,
            quality=self.qual_var.get(),
            audio_quality=self.audio_qual_var.get(),
            progress_hook=self._on_progress,
            done_hook=self._on_done,
            error_hook=self._on_error,
        )

    def _on_progress(self, d):
        if d.get("status") == "downloading":
            pct_str  = d.get("_percent_str", "0%").strip()
            size_str = d.get("_total_bytes_str",
                              d.get("_total_bytes_estimate_str", "")).strip()
            spd_str  = d.get("_speed_str", "").strip()
            eta_str  = d.get("_eta_str", "").strip()
            try:
                pct = float(re.sub(r"[^0-9.]", "", pct_str))
            except Exception:
                pct = 0
            self.after(0, lambda p=pct, ps=pct_str, ss=size_str,
                               sp=spd_str, es=eta_str:
                        self._update_progress(p, ps, ss, sp, es))
        elif d.get("status") == "finished":
            fname = d.get("filename", "")
            self.after(0, lambda f=fname:
                        self._log(f"Processing: {os.path.basename(f)}"))

    def _update_progress(self, pct, pct_str, size_str, spd_str, eta_str):
        self.prog_var.set(pct)
        self.prog_pct_var.set(pct_str)
        if size_str: self.prog_size_var.set(size_str)
        if spd_str:  self.prog_spd_var.set(f"⚡ {spd_str}")
        if eta_str:  self.prog_eta_var.set(f"⏱ {eta_str}")

    def _on_done(self):
        self.after(0, lambda: self._finish_download(True))

    def _on_error(self, err):
        self.after(0, lambda e=err: self._log(f"❌ Error: {e[:200]}"))
        self.after(0, lambda: self._finish_download(False))

    def _finish_download(self, success):
        self.is_downloading = False
        self.btn_download.config(state="normal")
        self.btn_cancel.config(state="disabled")
        ts    = datetime.now().strftime("%H:%M")
        title = self.info_title_var.get().replace("📄 ", "")[:50] \
                or self.url_var.get()[:50]
        if success:
            self.prog_var.set(100)
            self.prog_pct_var.set("100%")
            self.prog_spd_var.set("")
            self.prog_eta_var.set("")
            self.status_var.set("✅ Download complete!")
            self._log(f"✅ Saved to: {self.output_dir}")
            self.hist_tree.insert("", 0, values=(
                ts, title, self.mode_var.get().upper(), "✅ Done"))
            messagebox.showinfo("Done! 🎉",
                                 f"Download complete!\nSaved to: {self.output_dir}")
        else:
            self.status_var.set("❌ Download failed.")
            self.hist_tree.insert("", 0, values=(
                ts, title, self.mode_var.get().upper(), "❌ Failed"))

    def _cancel(self):
        self.dl.cancel()
        self.is_downloading = False
        self.btn_download.config(state="normal")
        self.btn_cancel.config(state="disabled")
        self.status_var.set("Cancelled.")
        self._log("⚠️ Download cancelled.")
        self.prog_var.set(0)
        self.prog_pct_var.set("0%")

    def _clear_history(self):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
        self._log("History cleared.")


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    App().mainloop()