# ⚡ GrabIt — Universal Video & Audio Downloader

Download videos and audio from YouTube, TikTok, Instagram, Twitter/X, Facebook, Reddit, SoundCloud, Vimeo, and 1000+ more sites.

---

## 🚀 How to Run

### 1. Install Python (if not installed)
Download from https://python.org (version 3.8+)

### 2. Install dependencies
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```

### 3. Run the Desktop App
```bash
python downloader.py
```

### 4. Run the Mobile/Modern UI
If you want to try the modern Flet-based interface (which also serves as the mobile version):
```bash
flet run main.py
```

---

## 📱 Android/Mobile Support (Flet)

This project includes a secondary frontend (`main.py` / `flet_app.py`) built with **Flet**, specifically designed for mobile layouts.

### How to Build the Android APK:
1. Ensure you have the [Flutter SDK](https://docs.flutter.dev/get-started/install) and Android Studio installed.
2. In your terminal, run:
   ```bash
   flet build apk
   ```
3. Once complete, you will find your compiled APK. Transfer it to your Android device to install and use!

*(Note: Because mobile platforms generally lack `ffmpeg` by default, this mobile version automatically downloads pre-merged `.mp4` video files to seamlessly ensure playback on your device.)*

---

## 🎯 Features
- Download videos from 1000+ sites (YouTube, TikTok, Instagram, Twitter/X, Facebook, Reddit, Vimeo, SoundCloud...)
- Audio-only MP3 extraction
- Quality selection: Best / 1080p / 720p / 480p
- Real-time progress bar with speed and ETA
- Download history log
- Custom save folder
- Fetch video info before downloading
- Cancel downloads mid-way

---

## 📋 Supported Sites (sample)
YouTube, TikTok, Instagram Reels/Posts, Twitter/X, Facebook Videos, Reddit, Twitch VODs, Vimeo, SoundCloud, Dailymotion, Bilibili, Pinterest, Mixcloud, Bandcamp, ESPN, and 1000+ more.

---

## 🛠 Requirements
- Python 3.8+
- yt-dlp (auto-installed)
- tkinter (comes with Python)
- ffmpeg (optional, for merging video+audio and MP3 conversion)

### Install ffmpeg (recommended)
- **Windows**: Download from https://ffmpeg.org/download.html and add to PATH
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

---

Built with Python + yt-dlp · by Ayman
