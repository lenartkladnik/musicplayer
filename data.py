import resources
from resources import ESCAPE_CODE, debug, print_
import requests
import bs4
import re
from spotify_background_color import SpotifyBackgroundColor
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import io
import time
from PIL import Image

class Lyrics:
    def __init__(self):
        pass
    
    def truncate(self, lst):
        result = []
        
        for i, item in enumerate(lst):
            if item != '\n' or (i > 0 and lst[i-1] != '\n'):
                result.append(item)
        
        return result

    def getFromGeniusUrl(self, song_url: str):
        """
        Get song lyrics from a genius search url
        """

        debug(f'Fetching lyrics from url: {song_url}.')
        response = requests.get(song_url)
        debug(f'Got response from url: {song_url}.')
        html = response.text
        soup = bs4.BeautifulSoup(html, 'html.parser')
        lyrics = []

        # All the divs that start with Lyrics-sc
        # which includes among other things the lyrics
        # for a song
        divs = soup.find_all('div', class_=re.compile('^Lyrics-sc'))
        for div in divs:
            # unfiltered_lyrics are lyrics + some promo and junk text
            unfiltered_lyrics = div.get_text(separator='\n', strip=True).splitlines()
            debug(f'Found lyrics in div.')
            for c, line in enumerate(unfiltered_lyrics):
                # First go trough the whole lyrics to determine if it should be 
                # split by <br/> tags or song sections
                if line == '[Intro]' or 'Lyrics' in line:
                    if '[' not in '\n'.join(unfiltered_lyrics[c:]):
                        # If the song doesn't have song sections it has to
                        # be split on double <br/> tags since they (usually)
                        # separate verses
                        debug("The lyrics don't have any song sections, splitting by <br> tags (less effective).")
                        div = str(div).replace('<br/><br/>', '\n\n')
                        div = bs4.BeautifulSoup(div, 'html.parser')
                        unfiltered_lyrics = div.get_text(separator='\n', strip=True).splitlines()
                    else:
                        debug("Splitting lyrics by song sections.")
                        # The splitting happens later

            debug(f'Filtering lyrics.')
            song_started = False
            rm_next_line = False
            for c, line in enumerate(unfiltered_lyrics):
                line = line.strip()

                if rm_next_line:
                    rm_next_line = False
                    debug(f'Got instruction to skip this line: {line}')
                    continue
                
                # Check if the song has started by seeing if the line says [Intro]
                # or if the song doesn't have song sections check for Lyrics since
                # it says Lyrics for 'song_title' at the start of almost every song
                if line == '[Intro]' or 'Lyrics' in line:
                    song_started = True

                if not song_started:
                    continue
                
                if line.startswith('['):
                    lyrics.append('')

                elif line == 'Embed':
                    continue

                elif line == 'You might also like':
                    continue


                elif line.startswith('See') and line.endswith('Live'):
                    rm_next_line = True # The next line is the ticket price
                    continue

                lyrics.append(line)
            
            if '\n'.join(Lyrics().truncate(lyrics[1:-1])).strip():
                debug(f'Lyrics found.')
                break
        
        truncated = Lyrics().truncate(lyrics[1:-1])
        resources.display_info('Successfully fetched lyrics.')

        return '\n'.join(truncated).strip() + '\n\n(' + song_url +')'

class GeniusURL:
    def __init__(self):
        self._wait = 2
        self._search_tries = 0

    def get(self, title: str, artists: str, driver):
        base_url = 'https://genius.com/'

        suffix = f"{resources.cleanTitleArtist(artists.replace(', ', ' and ').replace(' & ', ' and ').replace('&', ' and ')).replace(' ', '-')}-{resources.cleanTitleArtist(title).replace(' ', '-')}-lyrics"
        start_url = base_url + re.sub(r'-+', '-', suffix)

        resources.display_info(f"Trying with '{start_url}'.")

        driver.get(start_url)
        
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//img[starts-with(@alt, "Cover art for") and string-length(@src) > 0]')
                )
            )
        except Exception as e:
            pass
        
        song_url = driver.current_url

        if driver.find_elements(By.CLASS_NAME, "render_404-headline"):
            suffix = f"{resources.cleanTitleArtist(artists.split(', ')[0]).replace(' ', '-')}-{resources.cleanTitleArtist(title).replace(' ', '-')}-lyrics"
            start_url = base_url + re.sub(r'-+', '-', suffix)

            resources.display_info(f"Trying with '{start_url}'.")

            driver.get(start_url)
            song_url = driver.current_url

            if driver.find_elements(By.CLASS_NAME, "render_404-headline"):
                debug('Failed to get Genius url.')
                return ''
        
        debug(f'{song_url=}')

        return song_url
    
class CoverArt:
    def __init__(self):
        self._wait = 2
        self._search_tries = 0

    def getFromUrl(self, song_url: str, driver) -> str:
        try:
            driver.get(song_url)

            cover = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//img[starts-with(@alt, "Cover art for") and string-length(@src) > 0]')
                )
            )

            cover_src = cover.get_attribute('src')
            debug("Cover art URL: " + cover_src)
        except Exception as e: 
            print_(e)
        
        return cover_src
    
    def saveFromUrl(self, song_url: str, ascii_path: str, img_path: str, driver, density: dict, size: tuple[int, int]):
        url = self.getFromUrl(song_url, driver)

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
