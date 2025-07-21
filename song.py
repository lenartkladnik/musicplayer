import resources
import yt_dlp
import yt_dlp.downloader
from base64 import b64encode
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
from resources import print_

class Song:
    def __init__(self):
        self._wait = 3
        self._tries = 0
        self.rejected = False

    def downloadFromUrl(self, url: str, title: str, path: str, ext: str, title_encoding: str):
        URLS = [url]

        resources.display_info(f"Downloading '{url}' ({title})")

        ydl_opts = {
            'quiet': True if resources.DEBUG_LEVEL < 1 else False,
            'format': f'{ext}/bestaudio/best',
            'outtmpl': f'{path}/{b64encode(title.encode(title_encoding)).decode()}.{ext}',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': ext,
            }]
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download(URLS)

        except yt_dlp.utils.DownloadError:
            title = resources.cleanTitleArtist(title)

            ydl_opts['outtmpl'] = f'{path}/{b64encode(title.encode(title_encoding)).decode()}.{ext}'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download(URLS)

    def downloadFromSearch(self, search_string: str, title: str, path: str, driver, ext: str, title_encoding: str, max_tries: int = 10, xpath: str = '//a[@id="video-title"]'):
        self._tries += 1

        driver.get('https://www.youtube.com/')
        resources.debug('Page loaded.')

        time.sleep(1)

        actions = ActionChains(driver)

        for i in range(4):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.2)

        for i in search_string:
            actions.send_keys(i).perform()

        actions.send_keys(Keys.ENTER).perform()
        resources.debug('Search submitted.')

        try:
            video = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            resources.debug('Got video div.')
            video_url = video.get_attribute('href')
            resources.debug(f'Got video url: {video_url}')

        except Exception as e:
            if self._tries < max_tries:
                self._wait += 1
                resources.debug(f'Try {self._tries}.')
                resources.display_info(f'Try {self._tries} for getting audio.')
                return self.downloadFromSearch(search_string, title, path, driver, title_encoding, max_tries)
            
            raise TimeoutError('Could not download song.')

        if not video_url:
            print_('No video url.')
            if self._tries < max_tries:
                resources.debug(f'Try {self._tries}.')
                self._wait += 1
                return self.downloadFromSearch(search_string, title, path, title_encoding)
            
            raise TimeoutError('Could not download song.')
        
        return self.downloadFromUrl(video_url, title, path, ext, title_encoding)
