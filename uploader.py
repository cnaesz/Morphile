# uploader.py
import requests
import os

def upload_and_get_link(filepath):
    try:
        with open(filepath, 'rb') as f:
            response = requests.post(
                'https://file.io/?expires=1d',
                files={'file': f}
            )
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['link'], None
        return None, "آپلود ناموفق"
    except Exception as e:
        return None, str(e)