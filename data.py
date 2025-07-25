from os import truncate
import resources
from resources import ESCAPE_CODE, debug, print_
import requests
import urllib.parse
from spotify_background_color import SpotifyBackgroundColor
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import io
from PIL import Image

class Lyrics:
    def __init__(self):
        pass

    def truncate(self, lst) -> str:
        result = []

        for i, item in enumerate(lst):
            if item != '\n' or (i > 0 and lst[i-1] != '\n'):
                result.append(item)

        return '\n'.join(result)


    def get(self, search_string: str) -> str:
        r = requests.get("https://lyrics.kladnik.cc/?q=" + urllib.parse.quote(search_string)).text

        lyrics = "[" + r.split("[", 1)[1]
        lyrics = lyrics.replace("Ä", "č").replace("Å¡", "š").replace("Ðµ", "e")

        return self.truncate(lyrics.split('\n'))

class CoverArt:
    def __init__(self):
        self._wait = 2
        self._search_tries = 0

    def saveFromUrl(self, url: str, ascii_path: str, img_path: str, density: dict, size: tuple[int, int]):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            cover = Image.open(io.BytesIO(response.content))
            try:
                dc = SpotifyBackgroundColor(np.array(cover)).best_color()
                resources.debug(f'Got background color: {dc}.')
            except Exception:
                resources.debug('Failed to get background color. Using white as default.', 'error', ESCAPE_CODE + '[38m')
                dc = (255, 255, 255)

            with open(ascii_path, 'w+') as f:
                f.write(str(dc) + '\n')

            cover.save(img_path)
            
            debug(f"Image file saved to '{img_path}'. Dominant colour saved to '{ascii_path}'.")
            resources.display_info('Successfully fetched cover art.')
        else:
            resources.exception(f"Failed to download the file. Status code: {response.status_code}")
