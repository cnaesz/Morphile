# cleanup.py
import os
import time
import config

def cleanup_old_files():
    now = time.time()
    cutoff = now - (24 * 3600)  # 24 ساعت
    cleaned = 0
    folder = config.DOWNLOAD_DIR

    if not os.path.exists(folder):
        return

    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        if os.path.isfile(filepath):
            if os.path.getctime(filepath) < cutoff:
                try:
                    os.remove(filepath)
                    print(f"🧹 پاک شد: {filename}")
                    cleaned += 1
                except Exception as e:
                    print(f"❌ خطا در پاک کردن {filename}: {e}")
    print(f"✅ {cleaned} فایل قدیمی پاک شد.")