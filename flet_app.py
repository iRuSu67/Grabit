import flet as ft
import yt_dlp
import threading
import os
import re
from datetime import datetime

# Colors
DARK_BG = "#0d0d14"
SURFACE = "#17171f"
SURFACE2 = "#21212e"
ACCENT = "#7c6fff"
ACCENT2 = "#a78bfa"
TEXT = "#f0f0ff"
TEXT_MUTED = "#6b7280"

class DownloaderState:
    def __init__(self):
        self.cancelled = False

class GrabItApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "GrabIt Downloader"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = DARK_BG
        self.page.padding = 0
        self.page.scroll = ft.ScrollMode.ADAPTIVE
        # Mobile specific setup
        self.page.window_width = 400
        self.page.window_height = 800

        self.dl_state = DownloaderState()
        self.is_downloading = False
        self.history = []

        # Default mobile download dir
        self.output_dir = "/storage/emulated/0/Download"
        if os.name == "nt": # if on windows for testing
            self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        self.setup_ui()

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.value += f"[{ts}] {msg}\n"
        self.page.update()

    def setup_ui(self):
        # UI Elements for Download Tab
        self.url_input = ft.TextField(
            label="Video URL",
            hint_text="Paste YouTube, TikTok, IG link...",
            border_color=ACCENT,
            color=TEXT,
            bgcolor=SURFACE2,
        )

        self.mode_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="video", label="Video", fill_color=ACCENT),
                ft.Radio(value="audio", label="Audio", fill_color=ACCENT)
            ]),
            value="video",
            on_change=self.on_mode_change
        )

        self.qual_video_dropdown = ft.Dropdown(
            label="Video Quality",
            options=[
                ft.dropdown.Option("best", "Best"),
                ft.dropdown.Option("1080", "1080p"),
                ft.dropdown.Option("720", "720p"),
                ft.dropdown.Option("480", "480p")
            ],
            value="best",
            border_color=ACCENT,
            color=TEXT,
            bgcolor=SURFACE2,
        )

        self.qual_audio_dropdown = ft.Dropdown(
            label="Audio Quality",
            options=[
                ft.dropdown.Option("320", "320 kbps"),
                ft.dropdown.Option("192", "192 kbps"),
                ft.dropdown.Option("128", "128 kbps")
            ],
            value="320",
            border_color=ACCENT,
            color=TEXT,
            bgcolor=SURFACE2,
            visible=False
        )

        self.btn_fetch = ft.ElevatedButton("Fetch Info", on_click=self.fetch_info, bgcolor=SURFACE2, color=ACCENT)
        self.btn_download = ft.ElevatedButton("Download", on_click=self.start_download, bgcolor=ACCENT, color="white", disabled=True)
        self.btn_cancel = ft.ElevatedButton("Cancel", on_click=self.cancel_download, bgcolor=SURFACE2, color=ft.colors.RED_400, disabled=True)

        self.info_text = ft.Text("Ready. Paste URL to begin.", color=TEXT_MUTED, size=14)
        
        self.progress_bar = ft.ProgressBar(width=400, color=ACCENT, bgcolor=SURFACE2, value=0)
        self.progress_text = ft.Text("0%", color=TEXT_MUTED, size=12)
        
        self.log_text = ft.Text("", font_family="monospace", color=TEXT_MUTED, size=11, selectable=True)
        self.log_container = ft.Container(
            content=ft.Column([self.log_text], scroll=ft.ScrollMode.ALWAYS),
            height=150,
            bgcolor=SURFACE2,
            padding=10,
            border_radius=8
        )

        # Download Tab View
        self.view_download = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("GrabIt Downloader", size=24, weight="bold", color=ACCENT),
                self.url_input,
                ft.Row([self.btn_fetch]),
                self.info_text,
                ft.Divider(color=SURFACE2),
                ft.Text("Options", size=16, weight="bold", color=TEXT),
                self.mode_radio,
                self.qual_video_dropdown,
                self.qual_audio_dropdown,
                ft.Row([self.btn_download, self.btn_cancel], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(color=SURFACE2),
                self.progress_bar,
                self.progress_text,
                ft.Text("Log", size=14, weight="bold", color=TEXT),
                self.log_container
            ], scroll=ft.ScrollMode.ADAPTIVE)
        )

        # History Tab View
        self.history_list = ft.ListView(expand=True, spacing=10)
        self.view_history = ft.Container(
            padding=20,
            content=ft.Column([
                ft.Text("History", size=24, weight="bold", color=ACCENT),
                self.history_list
            ], expand=True)
        )

        # Setup Views
        self.content_area = ft.AnimatedSwitcher(
            content=self.view_download,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            reverse_duration=300,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True
        )

        self.page.navigation_bar = ft.NavigationBar(
            bgcolor=SURFACE,
            selected_index=0,
            on_change=self.on_nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.icons.DOWNLOAD, label="Download"),
                ft.NavigationBarDestination(icon=ft.icons.HISTORY, label="History"),
            ]
        )

        self.page.add(self.content_area)
        self._log("GrabIt Mobile Initialized.")
        if os.name == "nt":
            self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self._log(f"Save folder: {self.output_dir}")

    def on_nav_change(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self.content_area.content = self.view_download
        else:
            self.content_area.content = self.view_history
            self.update_history_ui()
        self.page.update()

    def on_mode_change(self, e):
        if self.mode_radio.value == "audio":
            self.qual_video_dropdown.visible = False
            self.qual_audio_dropdown.visible = True
        else:
            self.qual_video_dropdown.visible = True
            self.qual_audio_dropdown.visible = False
        self.page.update()

    def fetch_info(self, e):
        url = self.url_input.value.strip()
        if not url:
            self._log("No URL provided.")
            return

        self.btn_fetch.disabled = True
        self.btn_fetch.text = "Fetching..."
        self.info_text.value = "Fetching info..."
        self.page.update()

        def run():
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title", "Unknown")
                    dur = info.get("duration_string", "?")
                    
                    self.current_title = title
                    
                    def update_ui():
                        self.info_text.value = f"Found: {title[:50]} ({dur})"
                        self.btn_fetch.disabled = False
                        self.btn_fetch.text = "Fetch Info"
                        self.btn_download.disabled = False
                        self.page.update()
                    
                    self.page.run_thread(update_ui)
                    self._log(f"Fetched: {title[:40]}")
            except Exception as ex:
                def update_err():
                    self.info_text.value = "Error fetching info."
                    self.btn_fetch.disabled = False
                    self.btn_fetch.text = "Fetch Info"
                    self.page.update()
                self.page.run_thread(update_err)
                self._log(f"Error: {str(ex)[:60]}")

        threading.Thread(target=run, daemon=True).start()

    def start_download(self, e):
        url = self.url_input.value.strip()
        if not url or self.is_downloading:
            return

        self.is_downloading = True
        self.dl_state.cancelled = False
        
        self.btn_download.disabled = True
        self.btn_cancel.disabled = False
        self.progress_bar.value = 0
        self.progress_text.value = "0%"
        self.info_text.value = "Downloading..."
        self._log(f"Starting download...")
        self.page.update()

        mode = self.mode_radio.value
        vid_qual = self.qual_video_dropdown.value
        aud_qual = self.qual_audio_dropdown.value
        
        def run_dl():
            if mode == "audio":
                # Audio: fallback to best if no ffmpeg to extract mp3, typically on mobile we just dl m4a or bestaudio
                fmt = "bestaudio/best"
                # Remove postprocessor because mobile lacks ffmpeg usually
                postproc = []
            else:
                # Video: simple best without merger on mobile
                v_qual = "" if vid_qual == "best" else f"[height<={vid_qual}]"
                fmt = f"bestvideo{v_qual}[ext=mp4]+bestaudio[ext=m4a]/best{v_qual}/best"
                postproc = []

            os.makedirs(self.output_dir, exist_ok=True)
            outtmpl = os.path.join(self.output_dir, "%(title).60s.%(ext)s")
            
            opts = {
                "format": fmt,
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook],
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True, # Sometimes mobile needs this
            }
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                if not self.dl_state.cancelled:
                    self.page.run_thread(lambda: self._finish_dl(True))
            except Exception as ex:
                if not self.dl_state.cancelled:
                    self._log(f"Error: {str(ex)[:60]}")
                    self.page.run_thread(lambda: self._finish_dl(False))

        threading.Thread(target=run_dl, daemon=True).start()
        
    def _progress_hook(self, d):
        if self.dl_state.cancelled:
            raise Exception("Cancelled by user")
            
        if d.get("status") == "downloading":
            pct_str = d.get("_percent_str", "0%").strip()
            pct_str = re.sub(r"\\x1b\\[[0-9;]*m", "", pct_str) # Strip ansi colors
            
            try:
                pct = float(re.sub(r"[^0-9.]", "", pct_str)) / 100.0
            except Exception:
                pct = 0
                
            spd_str = d.get("_speed_str", "").strip()
            spd_str = re.sub(r"\\x1b\\[[0-9;]*m", "", spd_str)

            def ui_upd():
                self.progress_bar.value = pct
                self.progress_text.value = f"{pct_str} | Speed: {spd_str}"
                self.page.update()
            
            self.page.run_thread(ui_upd)
            
    def _finish_dl(self, success):
        self.is_downloading = False
        self.btn_download.disabled = False
        self.btn_cancel.disabled = True
        
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        title = getattr(self, "current_title", self.url_input.value[:30])
        mode = self.mode_radio.value.upper()
        
        if success:
            self.progress_bar.value = 1.0
            self.info_text.value = "Download complete!"
            self._log("Download finished.")
            self.history.append({"time": ts, "title": title, "mode": mode, "status": "Done"})
        else:
            self.info_text.value = "Download failed."
            self.history.append({"time": ts, "title": title, "mode": mode, "status": "Failed"})
            
        self.page.update()

    def cancel_download(self, e):
        self.dl_state.cancelled = True
        self.is_downloading = False
        self.btn_download.disabled = False
        self.btn_cancel.disabled = True
        self.info_text.value = "Cancelled."
        self._log("Download cancelled.")
        self.page.update()

    def update_history_ui(self):
        self.history_list.controls.clear()
        if not self.history:
            self.history_list.controls.append(ft.Text("No history yet.", color=TEXT_MUTED))
        else:
            for item in reversed(self.history):
                color = ft.colors.GREEN_400 if item["status"] == "Done" else ft.colors.RED_400
                self.history_list.controls.append(
                    ft.Container(
                        bgcolor=SURFACE2,
                        padding=10,
                        border_radius=8,
                        content=ft.Column([
                            ft.Text(item["title"], weight="bold", color=TEXT),
                            ft.Row([
                                ft.Text(item["time"], size=12, color=TEXT_MUTED),
                                ft.Text(item["mode"], size=12, color=ACCENT2)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(item["status"], color=color, size=12)
                        ])
                    )
                )
        self.page.update()

def main(page: ft.Page):
    GrabItApp(page)

if __name__ == "__main__":
    ft.app(target=main)
