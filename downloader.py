# downloader.py
import httpx
import os
import yt_dlp
from urllib.parse import urlparse
import config
import asyncio
import time

def get_filename_from_url(url):
    """Extracts a filename from a given URL."""
    try:
        parsed = urlparse(url)
        basename = os.path.basename(parsed.path)
        return basename if basename else "downloaded_file"
    except Exception:
        return "downloaded_file"

async def download_file(url, max_size=2 * 1024 * 1024 * 1024):
    """
    Asynchronously downloads a file, delegating to the appropriate
    downloader based on the URL.
    """
    # Simple check for media sites that yt-dlp handles well
    if any(site in url for site in ['youtube.com', 'youtu.be', 'vimeo.com', 'twitter.com']):
        return await download_audio_video(url, max_size)
    else:
        return await download_generic(url, max_size)

async def download_generic(url, max_size):
    """Asynchronously downloads a generic file from a URL."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with client.stream("GET", url, headers=headers) as r:
                r.raise_for_status()

                total_size = int(r.headers.get('content-length', 0))
                if total_size > max_size:
                    return None, f"File size ({total_size / 1024**2:.2f} MB) exceeds the maximum allowed size ({max_size / 1024**2:.2f} MB)."

                filename = get_filename_from_url(url)
                filepath = os.path.join(config.DOWNLOAD_DIR, f"{filename}_{int(time.time())}")
                os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

                downloaded = 0
                with open(filepath, 'wb') as f:
                    async for chunk in r.aiter_bytes(1024 * 1024):
                        if downloaded + len(chunk) > max_size:
                            os.remove(filepath)
                            return None, "Download exceeds the maximum file size limit."
                        f.write(chunk)
                        downloaded += len(chunk)

                return filepath, None
    except httpx.HTTPStatusError as e:
        return None, f"HTTP error occurred: {e.response.status_code} - {e.response.reason_phrase}"
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

def _blocking_yt_dlp_download(url, max_size):
    """
    Synchronous helper function to run yt-dlp.
    This function is intended to be run in a separate thread.
    """
    # Add a unique suffix to prevent filename collisions
    output_template = os.path.join(config.DOWNLOAD_DIR, '%(title)s_%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'best/bestvideo+bestaudio',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'max_filesize': max_size,
        'merge_output_format': 'mp4', # Merge to a standard format
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename, None

async def download_audio_video(url, max_size):
    """
    Asynchronously downloads audio/video using yt-dlp by running the
    blocking operation in a separate thread.
    """
    try:
        loop = asyncio.get_running_loop()
        # Run the synchronous yt-dlp download in a thread pool
        filepath, error = await loop.run_in_executor(
            None,  # Uses the default ThreadPoolExecutor
            _blocking_yt_dlp_download,
            url,
            max_size
        )
        if error:
            return None, error
        return filepath, None
    except Exception as e:
        # This will catch exceptions from within the yt-dlp execution
        return None, f"An error occurred with yt-dlp: {str(e)}"
