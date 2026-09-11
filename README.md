# 🎬 UltraTube 4K Studio - YouTube 4K Ultra-HD Downloader

> A high-performance, modern YouTube 4K Video and Audio Downloader featuring seamless separate stream merging powered by static FFmpeg, real-time WebSocket speed telemetry, playlist batch downloading, and a modern glassmorphic web interface.

---

## ✨ Features

- **True 4K Ultra-HD (2160p) & 60 FPS**: Downloads the highest bitrate 4K video stream and merges it losslessly with master audio.
- **Multiple Resolution Presets**:
  - 🎥 **4K Ultra-HD** (2160p @ 60fps)
  - 🎥 **2K Quad-HD** (1440p @ 60fps)
  - 🎥 **1080p Full HD** (1080p @ 60fps)
  - 🎥 **720p HD** & **480p SD**
- **Studio Audio Extraction**:
  - 🎵 **MP3 Extreme** (320 kbps)
  - 🎵 **MP3 Standard** (192 kbps)
  - 🎵 **M4A Lossless Source** (AAC)
  - 🎵 **WAV Uncompressed** (16-bit PCM)
- **Real-Time Live Telemetry**: Live progress percentage, download speed (MB/s), ETA countdown, and status indicators via WebSockets.
- **Playlist & Batch Support**: Automatically detects YouTube playlists and allows one-click batch downloading of all tracks.
- **Built-in Static FFmpeg**: Zero manual configuration required — static FFmpeg binary is automatically linked.
- **Download Library & Explorer Integration**: Direct browser downloads, history tracking, and one-click "Open in Windows Explorer".

---

## 🚀 Quick Start (One-Click)

### On Windows:
Simply double-click **`launch.bat`** in the project folder.

It will automatically launch the server and open the web app in your default browser at:
👉 **`http://localhost:8000`**

---

## 💻 Manual Launch via Terminal

1. Open PowerShell / Command Prompt in this folder.
2. Install requirements:
   ```bash
   python -m pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python server.py
   ```
4. Open your browser at `http://127.0.0.1:8000`.

---

## 📂 Where are Downloads Saved?

All downloaded videos and extracted audios are automatically saved to:
`C:\Users\<YourUsername>\Downloads\YouTube_4K_Downloads\`

You can also click the **"Open Folder"** button in the top navigation bar at any time to instantly view your downloaded files.
