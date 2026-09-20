import asyncio
import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import imageio_ffmpeg
import uvicorn
import yt_dlp
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Initialize Base App and Paths
app = FastAPI(title="UltraTube 4K Studio API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

BASE_DIR = Path(__file__).resolve().parent
if (BASE_DIR / "static").exists():
    STATIC_DIR = BASE_DIR / "static"
elif (BASE_DIR.parent / "static").exists():
    STATIC_DIR = BASE_DIR.parent / "static"
    BASE_DIR = BASE_DIR.parent
else:
    STATIC_DIR = Path.cwd() / "static"

try:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

if IS_VERCEL:
    DOWNLOADS_DIR = Path("/tmp") / "downloads"
    HISTORY_FILE = Path("/tmp") / "downloads_history.json"
    COOKIES_FILE = Path("/tmp") / "cookies.txt"
else:
    DOWNLOADS_DIR = Path.home() / "Downloads" / "YouTube_4K_Downloads"
    HISTORY_FILE = BASE_DIR / "downloads_history.json"
    COOKIES_FILE = BASE_DIR / "cookies.txt"

try:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Initialize Cookies from Environment Variable (for Vercel / Cloud / Docker)
def init_cookies_from_env():
    """Initializes cookies file from environment variables if present."""
    cookies_content = (
        os.environ.get("YOUTUBE_COOKIES_CONTENT")
        or os.environ.get("YOUTUBE_COOKIES")
        or os.environ.get("COOKIES_TEXT")
    )
    if not cookies_content:
        b64_content = os.environ.get("YOUTUBE_COOKIES_BASE64")
        if b64_content:
            try:
                import base64
                cookies_content = base64.b64decode(b64_content).decode("utf-8")
            except Exception:
                pass
    if cookies_content:
        try:
            with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                f.write(cookies_content.strip() + "\n")
            print(f"[Anti-Bot] Loaded YouTube cookies from environment variable ({len(cookies_content)} bytes)")
        except Exception as e:
            print(f"[Anti-Bot] Warning: Could not write cookies file: {e}")

init_cookies_from_env()

def get_cookie_file_path() -> Optional[str]:
    """Returns path to an active cookies file, or None if not configured."""
    env_file = os.environ.get("YOUTUBE_COOKIES_FILE")
    if env_file and os.path.exists(env_file):
        return env_file
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        return str(COOKIES_FILE)
    cwd_cookie = Path.cwd() / "cookies.txt"
    if cwd_cookie.exists() and cwd_cookie.stat().st_size > 0:
        return str(cwd_cookie)
    return None

# Configure static FFmpeg location safely
try:
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    FFMPEG_DIR = os.path.dirname(FFMPEG_EXE)
    if FFMPEG_DIR and FFMPEG_DIR not in os.environ.get("PATH", ""):
        os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
except Exception as e:
    FFMPEG_EXE = "ffmpeg"

# In-memory download tasks and websocket clients
active_tasks: Dict[str, Dict[str, Any]] = {}
ws_connections: Dict[str, List[WebSocket]] = {}
history_lock = threading.Lock()


def load_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(entry: Dict[str, Any]):
    with history_lock:
        hist = load_history()
        hist.insert(0, entry)
        hist = hist[:100]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")


def format_bytes(bytes_val: Optional[float]) -> str:
    if not bytes_val or bytes_val <= 0:
        return "Unknown size"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} PB"


def format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "Unknown"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


# Base yt-dlp configuration builder
def get_ydl_base_opts(strategy: str = "default", is_download: bool = False) -> Dict[str, Any]:
    cookie_path = get_cookie_file_path()

    opts: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": FFMPEG_EXE,
        "js_runtimes": {"node": {}},
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Mode": "navigate",
        },
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "windowsfilenames": True,
    }

    if cookie_path:
        opts["cookiefile"] = cookie_path

    # Configure strategy player clients
    if strategy == "default":
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["visionos", "web", "mweb", "android", "ios"],
            }
        }
    elif strategy == "mobile_fallback":
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["android", "ios", "mweb"],
            }
        }
    elif strategy == "tv_fallback":
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["tv", "mweb"],
            }
        }
    elif strategy == "web_safari":
        opts["extractor_args"] = {
            "youtube": {
                "player_client": ["web_safari", "android"],
            }
        }

    return opts


def extract_info_with_fallback(url: str, download: bool = False, custom_opts: Optional[dict] = None) -> Any:
    """
    Intelligently extracts info or downloads with multi-tier client fallback
    to seamlessly handle bot challenges, rate-limits, and SABR streams.
    """
    strategies = ["default", "mobile_fallback", "tv_fallback", "web_safari"]
    last_error = None

    for strat in strategies:
        opts = get_ydl_base_opts(strategy=strat, is_download=download)
        if custom_opts:
            opts.update(custom_opts)
            if "extractor_args" in custom_opts:
                opts["extractor_args"] = custom_opts["extractor_args"]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=download)
                if info:
                    return info
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "not a valid url" in err_str or "video unavailable" in err_str or "private video" in err_str:
                raise e
            continue

    if last_error:
        raise last_error
    raise Exception("Failed to fetch media info from YouTube.")


# Request / Response Schemas
class InfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format_id: str = "4k"  # '4k', '2k', '1080p', '720p', '480p', '360p', 'mp3-320', 'mp3-192', 'm4a', 'wav'
    custom_title: Optional[str] = None
    playlist_item_index: Optional[int] = None


class CookieSaveRequest(BaseModel):
    cookies_text: str


class CookieTestRequest(BaseModel):
    url: Optional[str] = "https://www.youtube.com/watch?v=LXb3EKWsInQ"


async def broadcast_progress(task_id: str, data: dict):
    if task_id in ws_connections:
        dead_sockets = []
        for ws in ws_connections[task_id]:
            try:
                await ws.send_json(data)
            except Exception:
                dead_sockets.append(ws)
        for ws in dead_sockets:
            if ws in ws_connections[task_id]:
                ws_connections[task_id].remove(ws)


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


# =========================================================================
# Cookie & Anti-Bot API Endpoints
# =========================================================================
@app.get("/api/cookies/status")
async def get_cookies_status():
    cookie_path = get_cookie_file_path()
    has_cookies = cookie_path is not None and os.path.exists(cookie_path)
    cookie_size = os.path.getsize(cookie_path) if has_cookies else 0
    return {
        "has_cookies": has_cookies,
        "cookie_file": cookie_path if has_cookies else None,
        "cookie_size_bytes": cookie_size,
        "is_cloud": IS_VERCEL,
        "status": "authenticated" if has_cookies else "ready_fallback",
        "message": (
            "YouTube Authentication Cookie is active (Anti-Bot Bypass enabled)."
            if has_cookies
            else "Using Multi-Client EJS Solver (No custom cookie active)."
        ),
    }


@app.post("/api/cookies/save")
async def save_cookies(req: CookieSaveRequest):
    content = req.cookies_text.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Cookies content cannot be empty.")

    try:
        with open(COOKIES_FILE, "w", encoding="utf-8") as f:
            f.write(content + "\n")
        return {
            "status": "success",
            "message": "Cookies saved successfully! Anti-Bot authentication is now active.",
            "file": str(COOKIES_FILE),
            "size": len(content),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save cookies: {str(e)}")


@app.post("/api/cookies/clear")
async def clear_cookies():
    try:
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
        return {
            "status": "success",
            "message": "Cookies removed. Engine returned to default multi-client mode.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete cookies: {str(e)}")


@app.post("/api/cookies/test")
async def test_cookies(req: CookieTestRequest):
    url = req.url.strip() if (req and req.url) else "https://www.youtube.com/watch?v=LXb3EKWsInQ"
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None, lambda: extract_info_with_fallback(url, download=False)
        )
        if not info:
            return {"success": False, "error": "No media info returned"}

        formats = info.get("formats", [])
        heights = sorted(list(set(f.get("height") for f in formats if f.get("height"))))
        return {
            "success": True,
            "title": info.get("title", "Video"),
            "uploader": info.get("uploader") or info.get("channel"),
            "formats_count": len(formats),
            "max_resolution": f"{max(heights, default=0)}p",
            "has_4k": max(heights, default=0) >= 2160,
            "available_heights": heights,
            "message": "Verification Successful! YouTube bot check passed seamlessly.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Test failed: {str(e)}",
        }


# =========================================================================
# Video Info Analysis Endpoint
# =========================================================================
@app.post("/api/info")
async def get_video_info(req: InfoRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: extract_info_with_fallback(
                url,
                download=False,
                custom_opts={"extract_flat": "in_playlist"},
            ),
        )
    except Exception as e:
        err_msg = str(e)
        needs_cookies = "sign in to confirm" in err_msg.lower() or "bot" in err_msg.lower()
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Failed to fetch video information: {err_msg}",
                "needs_cookies": needs_cookies,
            },
        )

    if not info:
        raise HTTPException(status_code=404, detail="No video found at provided URL")

    # Check if playlist
    is_playlist = info.get("_type") == "playlist" or "entries" in info

    if is_playlist:
        entries = []
        raw_entries = info.get("entries") or []
        for idx, entry in enumerate(raw_entries, 1):
            if not entry:
                continue
            entries.append(
                {
                    "index": idx,
                    "id": entry.get("id"),
                    "title": entry.get("title", f"Track {idx}"),
                    "duration": format_duration(entry.get("duration")),
                    "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                    "thumbnail": entry.get("thumbnail")
                    or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None),
                }
            )

        return {
            "is_playlist": True,
            "title": info.get("title", "YouTube Playlist"),
            "uploader": info.get("uploader") or info.get("channel", "Unknown Channel"),
            "playlist_count": len(entries),
            "entries": entries,
            "thumbnail": entries[0]["thumbnail"] if entries else None,
        }

    # Single video details
    formats = info.get("formats", [])
    has_4k = False
    has_2k = False
    has_1080p = False
    has_720p = False

    heights_seen = set()

    for f in formats:
        h = f.get("height")
        if h and h not in heights_seen and f.get("vcodec") != "none":
            heights_seen.add(h)
            if h >= 2160:
                has_4k = True
            elif h >= 1440:
                has_2k = True
            elif h >= 1080:
                has_1080p = True
            elif h >= 720:
                has_720p = True

    # Pre-calculated presets
    presets = []

    # 4K Preset
    if has_4k or max(heights_seen, default=0) >= 2160:
        presets.append({
            "id": "4k",
            "name": "4K Ultra-HD",
            "resolution": "2160p (3840x2160)",
            "badge": "4K UHD",
            "badge_color": "crimson",
            "type": "video",
            "ext": "mp4",
            "fps": 60,
            "description": "Crisp 4K Ultra High Definition with master audio",
            "available": True,
        })
    else:
        presets.append({
            "id": "4k",
            "name": "4K Ultra-HD",
            "resolution": "2160p (Upscaled/Best)",
            "badge": "4K",
            "badge_color": "muted",
            "type": "video",
            "ext": "mp4",
            "fps": 60,
            "description": "Best available resolution up to 4K",
            "available": False,
        })

    # 2K Preset
    if has_2k or max(heights_seen, default=0) >= 1440:
        presets.append({
            "id": "2k",
            "name": "2K Quad-HD",
            "resolution": "1440p (2560x1440)",
            "badge": "2K QHD",
            "badge_color": "purple",
            "type": "video",
            "ext": "mp4",
            "fps": 60,
            "description": "High resolution 1440p QHD Video",
            "available": True,
        })

    # 1080p Full HD Preset
    presets.append({
        "id": "1080p",
        "name": "1080p Full HD",
        "resolution": "1080p (1920x1080)",
        "badge": "1080p FHD",
        "badge_color": "blue",
        "type": "video",
        "ext": "mp4",
        "fps": 60,
        "description": "Crisp 1080p Full HD 60fps",
        "available": has_1080p or max(heights_seen, default=0) >= 1080,
    })

    # 720p HD Preset
    presets.append({
        "id": "720p",
        "name": "720p HD",
        "resolution": "720p (1280x720)",
        "badge": "720p HD",
        "badge_color": "teal",
        "type": "video",
        "ext": "mp4",
        "fps": 30,
        "description": "Fast download standard HD",
        "available": True,
    })

    # 480p
    presets.append({
        "id": "480p",
        "name": "480p Standard",
        "resolution": "480p SD",
        "badge": "480p SD",
        "badge_color": "gray",
        "type": "video",
        "ext": "mp4",
        "fps": 30,
        "description": "Lightweight standard definition",
        "available": True,
    })

    # Audio Presets
    audio_presets = [
        {
            "id": "mp3-320",
            "name": "MP3 Studio High",
            "resolution": "320 kbps Extreme",
            "badge": "MP3 320K",
            "badge_color": "amber",
            "type": "audio",
            "ext": "mp3",
            "description": "Master quality extracted MP3 audio",
            "available": True,
        },
        {
            "id": "mp3-192",
            "name": "MP3 Standard",
            "resolution": "192 kbps Clean",
            "badge": "MP3 192K",
            "badge_color": "amber",
            "type": "audio",
            "ext": "mp3",
            "description": "Optimized MP3 for mobile devices",
            "available": True,
        },
        {
            "id": "m4a",
            "name": "M4A Lossless Source",
            "resolution": "Native AAC",
            "badge": "M4A AAC",
            "badge_color": "amber",
            "type": "audio",
            "ext": "m4a",
            "description": "Direct YouTube high-fidelity audio stream",
            "available": True,
        },
        {
            "id": "wav",
            "name": "WAV Uncompressed",
            "resolution": "16-bit PCM",
            "badge": "WAV",
            "badge_color": "amber",
            "type": "audio",
            "ext": "wav",
            "description": "Uncompressed audio for editing and production",
            "available": True,
        },
    ]

    return {
        "is_playlist": False,
        "id": info.get("id"),
        "title": info.get("title", "Untitled Video"),
        "uploader": info.get("uploader") or info.get("channel", "Unknown Channel"),
        "duration": format_duration(info.get("duration")),
        "duration_raw": info.get("duration", 0),
        "view_count": f"{info.get('view_count', 0):,}" if info.get("view_count") else "N/A",
        "upload_date": info.get("upload_date"),
        "thumbnail": info.get("thumbnail")
        or (info.get("thumbnails", [{}])[-1].get("url") if info.get("thumbnails") else None),
        "max_resolution": f"{max(heights_seen, default=0)}p",
        "has_4k": has_4k,
        "video_presets": presets,
        "audio_presets": audio_presets,
    }


# =========================================================================
# Download Worker with Robust Stream Processing
# =========================================================================
def download_worker(task_id: str, url: str, format_id: str, loop: asyncio.AbstractEventLoop):
    task = active_tasks[task_id]

    def progress_hook(d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            percent = 0.0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)

            speed = d.get("speed")
            speed_str = f"{speed / (1024 * 1024):.2f} MB/s" if speed else "Calculating..."
            eta = d.get("eta")
            eta_str = f"{int(eta)}s" if eta else "Calculating..."

            task.update({
                "status": "downloading",
                "percent": percent,
                "downloaded_str": format_bytes(downloaded),
                "total_str": format_bytes(total),
                "speed_str": speed_str,
                "eta_str": eta_str,
                "current_file": os.path.basename(d.get("filename", "")),
                "stage": "Downloading high quality stream...",
            })

            asyncio.run_coroutine_threadsafe(
                broadcast_progress(task_id, task),
                loop,
            )
        elif status == "finished":
            task.update({
                "status": "processing",
                "percent": 99.0,
                "stage": "Merging video and audio streams with FFmpeg...",
            })
            asyncio.run_coroutine_threadsafe(
                broadcast_progress(task_id, task),
                loop,
            )

    out_template = str(DOWNLOADS_DIR / "%(title)s [%(id)s].%(ext)s")
    is_audio = format_id.startswith("mp3") or format_id in ["m4a", "wav", "flac"]

    custom_download_opts: Dict[str, Any] = {
        "outtmpl": out_template,
        "progress_hooks": [progress_hook],
    }

    if is_audio:
        if format_id == "mp3-320":
            custom_download_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    }
                ],
            })
        elif format_id == "mp3-192":
            custom_download_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            })
        elif format_id == "wav":
            custom_download_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    }
                ],
            })
        else:  # m4a
            custom_download_opts.update({
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                    }
                ],
            })
    else:
        # Video Formats
        if format_id == "4k":
            custom_download_opts.update({
                "format": "bestvideo[height<=2160]+bestaudio/best[height<=2160]/best",
                "merge_output_format": "mp4",
            })
        elif format_id == "2k":
            custom_download_opts.update({
                "format": "bestvideo[height<=1440]+bestaudio/best[height<=1440]/best",
                "merge_output_format": "mp4",
            })
        elif format_id == "1080p":
            custom_download_opts.update({
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
                "merge_output_format": "mp4",
            })
        elif format_id == "720p":
            custom_download_opts.update({
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
                "merge_output_format": "mp4",
            })
        elif format_id == "480p":
            custom_download_opts.update({
                "format": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
                "merge_output_format": "mp4",
            })
        else:
            custom_download_opts.update({
                "format": "bestvideo+bestaudio/best",
                "merge_output_format": "mp4",
            })

    try:
        task.update({
            "status": "starting",
            "stage": "Fetching media streams with anti-bot engine...",
            "percent": 0.0,
        })
        asyncio.run_coroutine_threadsafe(
            broadcast_progress(task_id, task),
            loop,
        )

        info = extract_info_with_fallback(
            url,
            download=True,
            custom_opts=custom_download_opts,
        )

        if not info:
            raise Exception("Failed to extract info for download")

        # Determine output file path
        with yt_dlp.YoutubeDL(custom_download_opts) as helper_ydl:
            final_filepath = helper_ydl.prepare_filename(info)

        if is_audio:
            target_ext = "mp3" if "mp3" in format_id else ("wav" if format_id == "wav" else "m4a")
            base, _ = os.path.splitext(final_filepath)
            final_filepath = f"{base}.{target_ext}"
        elif custom_download_opts.get("merge_output_format"):
            base, _ = os.path.splitext(final_filepath)
            final_filepath = f"{base}.{custom_download_opts['merge_output_format']}"

        # If merged file not found under predicted name, search downloads dir
        if not os.path.exists(final_filepath):
            video_id = info.get("id", "")
            for f in os.listdir(DOWNLOADS_DIR):
                if video_id in f:
                    final_filepath = str(DOWNLOADS_DIR / f)
                    break

        file_size_bytes = os.path.getsize(final_filepath) if os.path.exists(final_filepath) else 0
        filename = os.path.basename(final_filepath)

        history_entry = {
            "id": str(uuid.uuid4()),
            "title": info.get("title", filename),
            "filename": filename,
            "file_path": final_filepath,
            "file_size": format_bytes(file_size_bytes),
            "format": format_id.upper(),
            "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "thumbnail": info.get("thumbnail"),
            "duration": format_duration(info.get("duration")),
        }
        save_history(history_entry)

        task.update({
            "status": "completed",
            "percent": 100.0,
            "stage": "Download & Merging Complete! Saved to Downloads.",
            "file_path": final_filepath,
            "filename": filename,
            "file_size": format_bytes(file_size_bytes),
            "download_url": f"/api/files/{filename}",
        })
        asyncio.run_coroutine_threadsafe(
            broadcast_progress(task_id, task),
            loop,
        )
    except Exception as e:
        task.update({
            "status": "error",
            "error": str(e),
            "stage": f"Error: {str(e)}",
        })
        asyncio.run_coroutine_threadsafe(
            broadcast_progress(task_id, task),
            loop,
        )


@app.post("/api/download")
async def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    task_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()

    active_tasks[task_id] = {
        "task_id": task_id,
        "url": url,
        "format_id": req.format_id,
        "status": "queued",
        "percent": 0.0,
        "speed_str": "Connecting...",
        "eta_str": "--",
        "stage": "Queued in download manager",
        "downloaded_str": "0 MB",
        "total_str": "--",
    }

    thread = threading.Thread(
        target=download_worker,
        args=(task_id, url, req.format_id, loop),
        daemon=True,
    )
    thread.start()

    return {"task_id": task_id, "status": "started"}


@app.websocket("/api/ws/progress/{task_id}")
async def websocket_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    if task_id not in ws_connections:
        ws_connections[task_id] = []
    ws_connections[task_id].append(websocket)

    if task_id in active_tasks:
        await websocket.send_json(active_tasks[task_id])

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if task_id in ws_connections and websocket in ws_connections[task_id]:
            ws_connections[task_id].remove(websocket)


@app.get("/api/progress/{task_id}")
async def get_task_progress(task_id: str):
    if task_id in active_tasks:
        return active_tasks[task_id]
    raise HTTPException(status_code=404, detail="Task not found or completed")


@app.get("/api/history")
async def get_history():
    return load_history()


@app.delete("/api/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    with history_lock:
        hist = load_history()
        updated = [h for h in hist if h.get("id") != entry_id]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return {"status": "deleted"}


@app.get("/api/files/{filename}")
async def download_file(filename: str):
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )


@app.post("/api/open-folder")
async def open_downloads_folder():
    if IS_VERCEL:
        return {
            "status": "cloud",
            "message": "App is running in Cloud mode. Downloaded files are saved directly to your browser download folder.",
            "folder": str(DOWNLOADS_DIR),
        }
    try:
        if sys.platform == "win32":
            os.startfile(str(DOWNLOADS_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(DOWNLOADS_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(DOWNLOADS_DIR)])
        return {"status": "success", "folder": str(DOWNLOADS_DIR)}
    except Exception as e:
        return {"status": "error", "message": str(e), "folder": str(DOWNLOADS_DIR)}


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
elif (BASE_DIR / "static").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_candidates = [
        STATIC_DIR / "index.html",
        BASE_DIR / "static" / "index.html",
        Path.cwd() / "static" / "index.html",
        Path(__file__).resolve().parent / "static" / "index.html",
        Path(__file__).resolve().parent.parent / "static" / "index.html",
    ]
    for p in index_candidates:
        if p.exists():
            return HTMLResponse(content=p.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>UltraTube 4K Studio Starting...</h1>")


if __name__ == "__main__":
    import webbrowser

    port = 8000
    url = f"http://127.0.0.1:{port}"
    cookie_path = get_cookie_file_path()
    print(f"==================================================")
    print(f"  ULTRA-TUBE 4K STUDIO - YOUTUBE 4K DOWNLOADER")
    print(f"  Starting local server at: {url}")
    print(f"  Downloads saved to: {DOWNLOADS_DIR}")
    print(f"  FFmpeg location: {FFMPEG_EXE}")
    print(f"  Anti-Bot Protection: {'Cookies Active (' + str(cookie_path) + ')' if cookie_path else 'Multi-Client EJS Solver Active'}")
    print(f"==================================================")

    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
