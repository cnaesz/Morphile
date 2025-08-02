# downloader.py
import requests
import os
import yt_dlp
from urllib.parse import urlparse

def get_filename_from_url(url):
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path)
    return basename if basename else "downloaded_file"

def download_file(url, max_size=2 * 1024 * 1024 * 1024):
    if any(ext in url for ext in ['.mp3', '.mp4', '.wav', '.flac', 'youtube.com', 'youtu.be']):
        return download_audio_video(url, max_size)
    else:
        return download_generic(url, max_size)

def download_generic(url, max_size):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, stream=True, timeout=30)
        r.raise_for_status()

        total_size = int(r.headers.get('content-length', 0))
        if total_size > max_size:
            return None, "فایل بیش از حد بزرگ است (حداکثر 2 گیگ)"

        filename = get_filename_from_url(url) or "file"
        filepath = os.path.join(config.DOWNLOAD_DIR, filename)
        os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

        downloaded = 0
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(1024 * 1024):
                if downloaded + len(chunk) > max_size:
                    os.remove(filepath)
                    return None, "فایل در حین دانلود بیش از حد بزرگ شد"
                f.write(chunk)
                downloaded += len(chunk)

        return filepath, None
    except Exception as e:
        return None, str(e)

def download_audio_video(url, max_size):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(config.DOWNLOAD_DIR, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': max_size,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename, None
    except Exception as e:
        return None, str(e)