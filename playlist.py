from __future__ import division
import base64
import os
import requests
import urllib.parse
from song import Song
from math import floor, ceil
from data import Lyrics, CoverArt
from spotify_background_color import SpotifyBackgroundColor
import numpy as np
import vlc
import time
import resources
from resources import ESCAPE_CODE, cleanTitleArtist, print_
from base64 import b64encode, b64decode
import glob
import random
from datetime import datetime
from multiprocessing import Process
import shutil
from PIL import Image, UnidentifiedImageError
import traceback
import re

density = {
    'Ñ': 255,
    '@': 245,
    '#': 235,
    'W': 225, 
    '$': 215, 
    '9': 205, 
    '8': 195, 
    '7': 185, 
    '6': 175, 
    '5': 165, 
    '4': 155, 
    '3': 145, 
    '2': 135, 
    '1': 125, 
    '0': 115, 
    '?': 105, 
    '!': 95, 
    'a': 85, 
    'b': 75, 
    'c': 65, 
    ';': 55, 
    ':': 50, 
    '+': 45, 
    '=': 40, 
    '-': 35,
    '*': 20,
    ',': 10,
    '.': 5,
}

cwd = os.getcwd()
gray = resources.ESCAPE_CODE + "[38;5;240m"

class fp:
    PLAYLISTS = os.path.join(cwd, 'playlists')
    PLAYLIST = 'playlist'
    SONGS = 'songs'
    LYRICS = 'lyrics'
    COVER_ART = 'cover_art'

class mode:
    normal = 'normal'
    search = 'search'

class Playlist:
    def __init__(self, name: str, title_encoding='utf-16-le', no_cover: bool = False):
        if not os.path.exists(fp.PLAYLISTS):
            os.mkdir(fp.PLAYLISTS)

        self.title_encoding = title_encoding
        self.song_ext = 'm4a'
        self.lyrics_ext = 'lyrics'
        self.cover_ext = 'png'
        self.ascii_cover_ext = 'cover'
        self.queue_ext = 'queue'
        self.id_ext = 'id'

        self.main_fp = f'{fp.PLAYLISTS}/{name}'
        self.songs_fp = f'{self.main_fp}/{fp.SONGS}'
        self.lyrics_fp = f'{self.main_fp}/{fp.LYRICS}'
        self.cover_art_fp = f'{self.main_fp}/{fp.COVER_ART}'
        self.queue = f'{self.main_fp}/{name}.{self.queue_ext}'
        self.playlist_cover_fp = f'{self.main_fp}/{fp.PLAYLIST}.{self.cover_ext}'
        self.id_fp = f'{self.main_fp}/{name}.{self.id_ext}'

        self.bar = ['=', '+', '-']

        self.width, self.height = shutil.get_terminal_size((80, 20))
        self.height -= 2

        self.small_img = (floor(self.width / 12), floor(self.width / 24))
        self.giant_img = (floor(self.width / 5), floor(self.width / 10))
        self.tiny_img = (floor(self.width / 24), floor(self.width / 48))
        self.lyrics_width = (self.width - self.small_img[0] - self.giant_img[0] - 4 * 8)

        self.list_sel = 0
        self.start_area = 0
        self.initial_end = (self.height // (self.small_img[1])) - 1 + self.list_sel
        self.end_area = self.initial_end

        self.fwd_amount = 500
        self.interval = resources.REDRAW_INTERVAL

        self.leftover_scroll = self.height // 4

        self.shuffle = False
        self.current_song = 0
        self.playing = []

        self.default_dc = (66, 66, 66)

        self.songs = []

        self.mode = mode.normal

        self.player = None

        try:
            with open(self.id_fp, 'x') as f:
                f.write('')
        except:
            pass

        try:
            figlet_font = 'big.flf'
            self.font = resources.Figlet(figlet_font)

            for path in [self.main_fp, self.songs_fp, self.lyrics_fp, self.cover_art_fp]:
                if not os.path.exists(path):
                    os.mkdir(path)

            if not os.path.exists(self.queue):
                with open(self.queue, 'x') as f:
                    raw_songs = list(filter(os.path.isfile, glob.glob(self.songs_fp + "/*")))

                    songs = list(map(lambda x: x.rsplit('/', 1)[1].rsplit('.', 1)[0], raw_songs))

                    for raw, song in zip(raw_songs, songs):
                        f.write(f'{os.path.getmtime(raw)},{song}\n')

            self.songs = self.sortSongs(self.loadSongs())
            self.fix_integrity()

            if not os.path.exists(self.playlist_cover_fp) and not no_cover:
                self.createCover()

            elif os.path.exists(self.playlist_cover_fp):
                cover = Image.open(self.playlist_cover_fp)
                size = self.giant_img[0]

                for x in range(0, cover.width, size):
                    for y in range(0, cover.height, size):
                        block = cover.crop((x, y, x + size, y + size))
                        if block.getextrema() == ((255, 255), (255, 255), (255, 255)):
                            self.createCover()
                            break

                    else:
                        continue

                    break # Only executed if the inner loop breaks

            self.dcs = {}

            for song in self.songs:
                _, _, b64 = self.unpack_song(song)

                dc = self.default_dc

                try:
                    song_data = resources.getSongDataPath(self.cover_art_fp, b64, self.ascii_cover_ext)
                    if not song_data:
                        raise FileNotFoundError('Missing song data.')

                    with open(song_data) as f:
                        lines = f.read().splitlines()
                        tmp_dc = lines[0].strip()
                        if re.match(r'^\([0-9]{,3}\, ?[0-9]{,3}\, ?[0-9]{,3}\)$', tmp_dc): # Match because of eval statement
                            dc = eval(tmp_dc)

                    self.dcs.update(
                        {b64: dc}
                    )
                except Exception:
                    t, a, _ = self.unpack_song(song)
                    resources.display_info(f"Failed to load '{t} by {a}'.", 'warn', resources.ESCAPE_CODE + '[38;5;214m')
                    resources.debug(f'({b64=})', 'warn', resources.ESCAPE_CODE + '[38;5;214m')
                    self.songs.remove(song)

        except Exception:
            resources.debug(f'Got exception whilst loading playlist:')
            resources.debug(traceback.format_exc())
            try:
                self.fix_integrity()
            except Exception:
                resources.debug(f'Got exception whilst fixing playlist integrity:')
                resources.debug(traceback.format_exc())

                if input('This playlist seems to be corrupt (pass the "--debug" flag to see exception), would you like to delete it? [y/N] ').lower() == 'y':
                    shutil.rmtree(self.main_fp)
                    print_('Playlist deleted.')

                self.exit()

    def ensureResize(self):
        if resources.NO_AUTO_RESIZE:
            return False

        prev_size = (self.width, self.height)
        size = shutil.get_terminal_size((80, 20))

        if prev_size != size:
            self.width, self.height = size
            self.small_img = (floor(self.width / 12), floor(self.width / 24))
            self.giant_img = (floor(self.width / 5), floor(self.width / 10))
            self.tiny_img = (floor(self.width / 24), floor(self.width / 48))
            self.lyrics_width = (self.width - self.small_img[0] - self.giant_img[0] - 4 * 8)

            self.end_area = self.start_area + (self.height // (self.small_img[1])) - 1

            self.leftover_scroll = self.height // 4

            return True

        return False

    def findSongs(self) -> None:
        self.songs = self.loadSongs()
        b64s = []
        for f in os.listdir(self.songs_fp):
            if f.endswith(self.song_ext):
                b64 = f.split(self.song_ext)[0]
                bad = False
                for song in self.songs:
                    if len(song) <= 3:
                        continue

                    if self.unpack_song(song)[2] == b64:
                        bad = True
                        break
                if bad:
                    continue

                resources.debug(f"Found new song: {base64.b64decode(b64).decode(self.title_encoding)}")
                b64s.append(b64)

        songs = []
        for b64 in b64s:
            songs.append([str(datetime.now().timestamp()), b64])

        with open(self.queue, 'a') as f:
            for song in songs:
                _, _, b64 = self.unpack_song(song)
                f.write(f'{song[0]},{b64}\n')

        self.songs = self.loadSongs()

    def cleanupSongData(self):
        to_cleanup = []
        for f in os.listdir(self.lyrics_fp):
            b64 = f.split("." + self.lyrics_ext)[0]

            resources.debug(f"Checking: {os.path.join(self.songs_fp, b64 + "." + self.song_ext)}", level=2)

            if not os.path.exists(os.path.join(self.songs_fp, b64 + "." + self.song_ext)):
                to_cleanup.append(b64)

        resources.debug(f"Removing: {to_cleanup}");

        removed = []

        for b64 in to_cleanup:
            try:
                os.remove(self.lyrics_fp + "/" + b64 + "." + self.lyrics_ext)
            except OSError as e: resources.debug(f"Error whilst removing '{self.lyrics_fp + b64 + self.lyrics_ext}': {e}", level=2)
            try:
                os.remove(self.cover_art_fp + "/" + b64 + "." + self.cover_ext)
            except OSError as e: resources.debug(f"Error whilst removing '{self.cover_art_fp + b64 + self.cover_ext}': {e}", level=2)
            try:
                os.remove(self.cover_art_fp + "/" + b64 + "." + self.ascii_cover_ext)
            except OSError as e: resources.debug(f"Error whilst removing '{self.cover_art_fp + b64 + self.ascii_cover_ext}': {e}", level=2)
            try:
                os.remove(self.songs_fp + "/" + b64 + "." + self.song_ext)
            except OSError as e: resources.debug(f"Error whilst removing '{self.songs_fp + b64 + self.song_ext}': {e}", level=2)

            removed.append(b64)

        return removed

    def generateSongFromb64(self, b64: str, timestamp: float | str | None = None) -> list[str]:
        if not timestamp: timestamp = datetime.now().timestamp()
        return [str(timestamp), *b64decode(b64).decode(self.title_encoding).split(' by '), b64]

    def fix_integrity(self):
        self.findSongs()

        filtered = []
        for f in os.listdir(self.songs_fp):
            b64 = f.split("." + self.song_ext)[0]
            try: b64decode(b64)
            except:
                resources.debug('Invalid base 64 string for unknown song.')
                continue

            if not resources.existsSongData(self.songs_fp, b64):
                resources.debug(f'Missing audio for {b64decode(b64).decode(self.title_encoding)}.')
                continue

            if not resources.existsSongData(self.lyrics_fp, b64):
                resources.debug(f'Missing lyrics for {b64decode(b64).decode(self.title_encoding)}.')
                with open(f'{self.lyrics_fp}/{b64}.{self.lyrics_ext}', 'x') as f:
                    f.write(f"Ops couldn't get the lyrics for this one.\n")

            if not resources.existsSongData(self.cover_art_fp, b64, self.cover_ext):
                resources.debug(f'Missing cover art image for {b64decode(b64).decode(self.title_encoding)}.')
                Image.new('RGB', (1, 1), 'white').save(f'{self.cover_art_fp}/{b64}.{self.cover_ext}')

            else:
                try:
                    with Image.open(resources.getSongDataPath(self.cover_art_fp, b64, self.cover_ext)) as _: pass
                except UnidentifiedImageError:
                    song_data = resources.getSongDataPath(self.cover_art_fp, b64)
                    if song_data:
                        os.remove(song_data)
                    Image.new('RGB', (1, 1), 'white').save(resources.getSongDataPath(self.cover_art_fp, b64))

            if not resources.existsSongData(self.cover_art_fp, b64, self.ascii_cover_ext):
                resources.debug(f'Missing cover ascii art for {b64decode(b64).decode(self.title_encoding)}.')

                dc = self.default_dc

                with open(f'{self.cover_art_fp}/{b64}.{self.ascii_cover_ext}', 'w+') as f:
                    f.write(str(dc) + '\n')

            filtered.append(b64)

        removed = self.cleanupSongData()
        filtered = list( set(filtered) - set(removed) )
        self.songs = [self.generateSongFromb64(b64) for b64 in filtered]
        self.createCover()

        resources.debug(f'Writting: {self.songs}')

        with open(self.queue, 'w') as f:
            for song in self.songs:
                f.write(f'{song[0]},{self.unpack_song(song)[2]}\n')

    def existsSong(self, title: str, artists: str) -> bool:
        title = title.split(' - ')[0].strip()
        resources.debug(f"Checking if '{title}', '{artists}' exists in playlist.", level=1)

        for song in self.songs:
            t, a, _ = self.unpack_song(song)
            if t == title and a == artists:
                resources.debug('Song exists in playlist.')
                return True

        title = self._truncateTitle(title)
        artists = self._truncateArtists(artists)

        resources.debug(f"Title and artists modified: '{title}', '{artists}'.", level=2)

        for song in self.songs:
            t, a, _ = self.unpack_song(song)
            if t == title and a == artists:
                resources.debug('Song exists in playlist.')
                return True

        resources.debug('Song does not exist in playlist.')

        return False

    def createCover(self):
        images = []
        for i in range(4):
            if i < len(self.songs):
                b64 = self.songs[i][3]
                images.append(Image.open(resources.getSongDataPath(self.cover_art_fp, b64, self.cover_ext)))
            else:
                images.append(None)

        size = self.giant_img[0]
        cover = Image.new('RGB', (size * 2, size * 2), 'black')

        pos = [(0, 0), (size, 0), (0, size), (size, size)]

        for pos, img in zip(pos, images):
            if img != None:
                img = img.resize((size, size))
            else:
                img = Image.new('RGB', (size, size), self.default_dc)

            x, y = pos

            cover.paste(img, (x, y))

        cover.save(self.playlist_cover_fp)

    def shuffleSongs(self, songs: list[list[str]]) -> list[list[str]]:
        songs_copy = songs.copy()
        random.shuffle(songs_copy)

        return songs_copy

    def sortSongs(self, songs: list[list[str]]) -> list[list[str]]:
        songs.sort(key=lambda x: float(x[0]))

        return songs

    def loadSongs(self) -> list[list[str]]:
        with open(self.queue) as f:
            raw = list(map(lambda x: x.split(','), f.read().splitlines()))

        songs = [self.generateSongFromb64(i[1], i[0]) for i in raw]

        return songs

    def remove_playlist(self):
        shutil.rmtree(self.main_fp)
        print_('Playlist deleted.')

    def remove_song(self, search_string: str) -> bool:
        match = False
        for song in self.songs:
            title, artists, b64 = self.unpack_song(song)

            if resources.matching(f'{title}', search_string) or resources.matching(f'{artists}', search_string):
                if input(f'Delete {title} by {artists}? [y/N]').lower() == 'y':
                    self.songs.remove(song) 

                    song_data = resources.getSongDataPath(self.songs_fp, b64)
                    if not song_data: break
                    os.remove(song_data)
                    self.fix_integrity()

                    match = True

        if not match:
            print_('No song by that name was found.')

        return match

    def _remove_song(self, song: list[str]) -> bool:
        b64 = self.unpack_song(song)[2]

        self.songs.remove(song)

        song_data = resources.getSongDataPath(self.songs_fp, b64)
        if not song_data: return False
        os.remove(song_data)
        self.fix_integrity()

        return True

    def _truncateArtists(self, artists: str) -> str:
        artists = artists.split(',')[0]

        return artists

    def _truncateTitle(self, title: str) -> str:
        title = re.sub(r'\(.+\)|\[.+\]', '', title)
        title = ' '.join(title.split())

        return title

    def add(self, search_string: str, driver, lyrics: bool = True):
        title, artists = self._addFromGenius(search_string, lyrics)
        self._addFromYt(title, artists, driver)

    def _addFromYt(self, title: str, artists: str, driver):
        resources.display_info(f"Adding audio for '{title} by {artists}'.")

        song = Song()
        tries = 0

        while True:
            try:
                song.downloadFromSearch(f'{title} by {artists}', f'{title} by {artists}', self.songs_fp, driver, self.song_ext, self.title_encoding)
                break
            except Exception:
                resources.debug(f'Got exception whilst downloading audio:')
                resources.debug(traceback.format_exc())

                if tries == 1: # Usually filename too long.
                    title = self._truncateTitle(title)
                    artists = self._truncateArtists(artists)

                if tries >= 10:
                    print_(resources.ESCAPE_CODE + f"[38;5;203mFailed to get audio for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m")
                    return False

                print_(resources.ESCAPE_CODE + f"[38;5;220mCould not get audio for '{title} by {artists}'. Trying again." + resources.ESCAPE_CODE + "[0m")
                tries += 1

        print_(resources.ESCAPE_CODE + f"[38;5;40mSuccessfully downloaded audio for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m")
        resources.successes['audio'] += 1
        return True

    def _addFromGenius(self, search_string: str, get_lyrics: bool = True) -> list[str]:
        success = True

        try:
            title, artists = search_string.split(' by ')
        except:
            title, artists = ('', '')
        search_string = cleanTitleArtist(search_string).lower().split(', ')[0]

        resources.debug(f"Querying Genius API with q={search_string}")

        template = "https://genius.com/api/search/multi?experiment=not-eligible&per_page=5&q=" + urllib.parse.quote(search_string)

        r = requests.get(template)

        if r.status_code != 200:
            print_(resources.ESCAPE_CODE + f"[38;5;203mFailed to download lyrics and cover art for '{search_string}'." + resources.ESCAPE_CODE + "[0m")
            return ['', '']

        json_r = r.json()

        result = {}
        for section in json_r['response']['sections']:
            if section['type'] == 'song':
                for hit in section['hits']:
                    hit_title = hit['result']['title']
                    hit_artist = hit['result']['primary_artist']['name']

                    if title and artists:
                        if title.lower() in hit_title.lower() and artists.lower() in hit_artist.lower():
                            result = hit['result']

                    else:
                        title, artists = (hit_title, hit_artist)
                        result = hit['result']
                        break

        if not result:
            resources.debug("Couldn't get accurate result from Genius API, trying a more general approach.", 'warn')
            result = json_r["response"]["sections"][0]["hits"][0]["result"]

        cover_art_url = ""
        if result:
            for i in ["header_image_url", "cover_art_url", "header_image_thumbnail_url", "song_art_image_thumbnail_url"]:
                try:
                    cover_art_url = result[i]
                    break
                except KeyError:
                    pass

        resources.debug(f"Got cover art url: {cover_art_url}")

        b64rep = b64encode(f"{title} by {artists}".encode(self.title_encoding)).decode()

        coverArt = CoverArt()
        try:
            coverArt.saveFromUrl(cover_art_url, f'{self.cover_art_fp}/{b64rep}.{self.ascii_cover_ext}', f'{self.cover_art_fp}/{b64rep}.{self.cover_ext}')
        except Exception:
            resources.debug(f'Got exception whilst getting cover art:')
            resources.debug(traceback.format_exc())
            print_(resources.ESCAPE_CODE + f"[38;5;203mFailed to get cover art for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m") 
            success = False

        if get_lyrics:
            try:
                lyrics = Lyrics().get(search_string.replace(' by ', ' - ', 1))
                with open(f'{self.lyrics_fp}/{b64rep}.{self.lyrics_ext}', 'w') as f:
                    f.write(lyrics)

            except Exception:
                resources.debug(f'Got exception whilst getting lyrics:')
                resources.debug(traceback.format_exc())
                print_(resources.ESCAPE_CODE + f"[38;5;203mFailed to get lyrics for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m")
                success = False

        try:
            Image.open(resources.getSongDataPath(self.cover_art_fp, b64rep, self.cover_ext))
        except UnidentifiedImageError:
            if not resources.existsSongData(self.cover_art_fp, b64rep, self.cover_ext) and not resources.existsSongData(self.cover_art_fp, b64rep, self.ascii_cover_ext):
                raise FileNotFoundError('Missing song data.')

            os.remove(resources.getSongDataPath(self.cover_art_fp, b64rep, self.cover_ext))
            os.remove(resources.getSongDataPath(self.cover_art_fp, b64rep, self.ascii_cover_ext))

            Image.new('RGB', (1, 1), self.default_dc).save(resources.getSongDataPath(self.cover_art_fp, b64rep, self.cover_ext))
            im = Image.open(resources.getSongDataPath(self.cover_art_fp, b64rep, self.cover_ext))
            try:
                dc = SpotifyBackgroundColor(np.array(im)).best_color()
                resources.debug(f'Got background color: {dc}.')
            except Exception:
                resources.debug('Failed to get background color. Using white as default.', 'error', resources.ESCAPE_CODE + '[31m')
                dc = self.default_dc

            with open(resources.getSongDataPath(self.cover_art_fp, b64rep, self.ascii_cover_ext), 'w+') as f:
                f.write(str(dc) + '\n')

        except Exception:
            resources.debug('Got exception whilst checking cover art:')
            resources.debug(traceback.format_exc())

        if success:
            print_(resources.ESCAPE_CODE + f"[38;5;40mSuccessfully downloaded lyrics and cover art for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m")
            resources.successes['cover_art'] += 1
            resources.successes['lyrics'] += 1

        else:
            print_(resources.ESCAPE_CODE + f"[38;5;203mFailed to download lyrics and cover art for '{title} by {artists}'." + resources.ESCAPE_CODE + "[0m")

        if resources.getch() == 'q':
            self.exit()

        return [title, artists]

    def unpack_song(self, song: list[str]):
        if len(song) == 2:
            # Broken song; with (probably) timestamp and base64 string
            d = b64decode(song[1]).decode(self.title_encoding).split(' by ')

            if len(d) == 1:
                return [d[0], '', song[1]]

            return [d[0], d[1], song[1]]

        elif len(song) == 3:
            # Broken song; (probably) without artists
            return [song[1], '', song[2]]

        return [song[1], song[2], song[3]]

    def add_batch(self, titles: list[str], artists_list: list[str], instances, lyrics: bool = True):
        to_add = []
        for title, artists in zip(titles, artists_list):
            if not self.existsSong(title, artists):
                to_add.append([title, artists])

        for title, artists in to_add:
            self._addFromYt(title, artists, resources.drivers[0])

        inst = 0
        processes: list[Process] = []
        for title, artists in to_add:
            proc = Process(target=self._addFromGenius, args=(title + " by " + artists, lyrics))
            processes.append(proc)
            proc.start()

            inst = (inst + 1) % instances

            if inst == instances - 1:
                for proc in processes:
                    processes.remove(proc)
                    proc.join()

        for proc in processes:
            proc.join()

    def existsSongInList(self, title: str, artists: str):
        for song in self.songs:
            song_title, song_artists, _ = self.unpack_song(song)
            if resources.matching(song_title, title) and resources.matching(song_artists, artists):
                return True

        return False

    class SyncType:
        spotify: str = 'spotify'

    def sync(self, type_: str, id: str, do_lyrics: bool = True):
        disable_stdout_state = resources.DISABLE_STDOUT
        if not resources.DEBUG:
            resources.DISABLE_STDOUT = True

        if not resources.DEBUG and not disable_stdout_state:
            print(f'Initializing drivers...\r', end='')

        resources._init_selenium_driver()

        if not resources.DEBUG and not disable_stdout_state:
            print(f'{ESCAPE_CODE}[B', end='')

        not_parsed = []

        songs = []
        if type_ == self.SyncType.spotify:
            spotify = resources.Spotify()
            songs, id = spotify.get_songs(id)

        bar = None
        if not resources.DEBUG:
            text = "Syncing..."
            bar = resources.progressBar(len(songs), self.width - len(text) - (len(str(len(songs))) * 2) - 6, text)
            bar.start()

        for song in songs:
            if song and not self.existsSongInList(*song):
                self.add(' by '.join(song), resources.drivers[0], do_lyrics)

            else:
                not_parsed.append(' by '.join(song))

            if bar:
                resources.DISABLE_STDOUT = False
                bar.next()
                if not resources.DEBUG:
                    resources.DISABLE_STDOUT = True

        self.fix_integrity()

        print_(resources.ESCAPE_CODE + '[38;5;40mDone.' + resources.ESCAPE_CODE + '[0m')
        print_("Skipped these because they were deemed to be already in the playlist:")
        for i in not_parsed:
            print_(f"    - {i}")
        print_()

        resources.drivers[0].quit()

        with open(self.id_fp, 'w+') as f:
            new_ids = []
            for ln in f.readlines():
                if ln.split(':')[1] == id and ln.split(':')[0] == type_:
                    continue

                new_ids.append(ln)

            new_ids.append(f"{type_}:{id}:{'1' if do_lyrics else '0'}")

            f.write('\n'.join(new_ids))

        resources.DISABLE_STDOUT = disable_stdout_state
        print_("\x1b[2A")

    def update_display(self, buffer: list, instructions: str | None = ''):
        buffer = [';'] + buffer
        if instructions:
            buffer = [instructions] + buffer

        resources.reset_screen()
        for ln in buffer:
            print_(resources.ESCAPE_CODE + '[2K' + ''.join(ln).ljust(self.width))

        print_(resources.ESCAPE_CODE + f'[{len(buffer) + 1}A', end='')

    def list_view(self, songs: list[list[str]] | None = None):
        if not songs:
            songs = self.songs

        resources.reset_screen()

        self._update_list_view(songs)

        while True:
            count = len(songs) - 1

            if self.ensureResize():
                self._update_list_view(songs)

            ch = resources.getch()

            if any([x == ch for x in resources.Keybinds.control.enter]):
                if ch == '\n':
                    print_(resources.ESCAPE_CODE + '[A', end='')

                try:
                    self.play_view(songs[self.list_sel])
                except IndexError:
                    pass

                return

            elif any([x == ch for x in resources.Keybinds.navigation.up]):
                self.list_sel = self.list_sel - 1 if self.list_sel > 0 else 0
                if self.list_sel <= self.start_area and self.list_sel > 0:
                    self.start_area -= 1
                    self.end_area -= 1

                self._update_list_view(songs)

            elif any([x == ch for x in resources.Keybinds.navigation.down]):
                self.list_sel = self.list_sel + 1 if self.list_sel < count else self.list_sel
                if self.list_sel >= self.end_area and self.list_sel < count + 1:
                    self.start_area += 1
                    self.end_area += 1

                self._update_list_view(songs)

            elif any([x == ch for x in resources.Keybinds.common.quit]):
                return

            elif any([x == ch for x in resources.Keybinds.common.back]):
                if self.mode == mode.search:
                    songs = self.songs

                self.mode = mode.normal

                self.list_sel = 0
                self.start_area = 0
                self.end_area = self.initial_end
                self.current_song = 0

                self._update_list_view(songs)

            elif any([x == ch for x in resources.Keybinds.common.shuffle]):
                self.shuffle = True
                songs = self.shuffleSongs(songs)
                self.playing = songs

                self.handle_next()
                return

            elif any([x == ch for x in resources.Keybinds.extra_actions]):
                string = str(ch) + input(ch)

                if any([string.startswith(x) for x in resources.Keybinds.common.search]):
                    self.mode = mode.search

                    self.handle_search(string[1:])
                    return

                elif string == f'{resources.Key.common.command}{resources.Keybind.goto.top}':
                    self.list_sel = 0
                    self.start_area = 0
                    self.end_area = self.initial_end
                    self.current_song = 0

                    self._update_list_view(self.songs)

                elif string == f'{resources.Key.common.command}{resources.Keybind.goto.bottom}':
                    self.list_sel = count
                    self.start_area = count
                    self.end_area = self.initial_end + count
                    self.current_song = count

                    self._update_list_view(self.songs)

                elif string == f'{resources.Key.common.command}remove':
                    b64 = self.unpack_song(songs[self.list_sel])[2]

                    songs.pop(self.list_sel)
                    self.songs = songs

                    try:
                        os.remove(str(resources.getSongDataPath(self.songs_fp, b64, self.song_ext)))
                    except:
                        pass

                    count -= 1
                    if self.list_sel > 0:
                        self.list_sel -= 1

                    self.fix_integrity()
                    self.songs = self.sortSongs(self.loadSongs())
                    songs = self.songs

                    self._update_list_view(self.songs)

                elif string.startswith(f'{resources.Key.common.command}add '):
                    string = string.split('add ', 1)[1].replace(' - ', ' by ')

                    resources.display_info_mode = True
                    resources._init_selenium_driver()

                    self.add(string, resources.drivers[0])

                    # Create playlist cover
                    self.createCover()
                    resources.display_info_mode = False

                    count += 1
                    if self.list_sel < count:
                        self.list_sel += 1

                    self.fix_integrity()
                    self.songs = self.sortSongs(self.loadSongs())
                    songs = self.songs

                    self._update_list_view(self.songs)

                    resources.drivers[0].quit()

                elif string.startswith(f'{resources.Key.common.command}sync '):
                    to_sync = string.split('sync ')[1]
                    self.sync(self.SyncType.spotify, to_sync)

                elif string.startswith(f'{resources.Key.common.command}sync'):
                    to_sync = [];
                    with open(self.id_fp, 'r') as f:
                        for l in f.readlines():
                            to_sync.append(l.split(':'))

                    for el in to_sync:
                        self.sync(el[0], el[1], '1' in el[2])

                elif string.startswith(resources.Key.common.command):
                    self._update_list_view(self.songs)

            time.sleep(self.interval)

    def _update_list_view(self, songs):
        buffer = []
        w, h = self.small_img

        for idx, song in enumerate(songs[self.start_area:self.end_area]):
            title, artist, b64 = self.unpack_song(song)

            cover_art = resources.coverArtToText(resources.getSongDataPath(self.cover_art_fp, b64, self.cover_ext), density, w, h)

            max_len = max(40, len(title), len(artist))

            idx += self.start_area
            ln_sel = idx == self.list_sel

            if ln_sel:
                buffer.append(f'╭{"─" * (max_len + w + 4)}╮')

            for c, ln in enumerate(cover_art.splitlines()):
                buffer.append(f'{"│" if ln_sel else " "}{ln}{" " * 4}{title.ljust(max_len) if c == 1 else ""}{(gray + artist.ljust(max_len) + resources.ESCAPE_CODE + "[0m") if c == 2 else " " * max_len if c != 1 else ""}' + resources.ESCAPE_CODE + f'[0m{"│" if ln_sel else " "}')

            if ln_sel:
                buffer.append(f'╰{"─" * (max_len + w + 4)}╯')

        self.update_display(buffer, resources.ESCAPE_CODE + '[A')

    def handle_search(self, string):
        matches = []

        for song in self.songs:
            title, artists, _ = self.unpack_song(song)

            for s in string.split('/'):
                if resources.matching(title, s) or any([resources.matching(x, s) for x in artists.split(', ')]):
                    resources.debug(f'Match found: {song}.')
                    matches.append(song)

        self.list_sel = 0
        self.start_area = 0
        self.end_area = self.initial_end
        self.current_song = 0

        self.list_view(matches)

    def handle_next(self):
        if self.shuffle:
            songs = self.playing
            self.current_song += 1

            if self.current_song >= len(songs):
                self.current_song = 0
                songs = self.shuffleSongs(songs)

            if not resources.DEBUG: print_() # Fix exit when playing song from search without debug mode on

            self.play_view(songs[self.current_song])

        else:
            self.list_view()

    def play_view(self, song: list[str]):
        resources.reset_screen()

        title, artist, b64 = self.unpack_song(song)

        w_p, h_p = self.small_img
        playlist_cover = resources.coverArtToText(f'{self.main_fp}/{fp.PLAYLIST}.{self.cover_ext}', density, w_p, h_p)

        w_c, h_c = self.giant_img
        dc = self.dcs[b64]
        cover_art = resources.coverArtToText(resources.getSongDataPath(self.cover_art_fp, b64, self.cover_ext), density, w_c, h_c)

        lyrics = []
        with open(resources.getSongDataPath(self.lyrics_fp, b64), 'r') as f:
                lyrics = f.read().splitlines()[:-2]
        lyrics = Lyrics().cleanup('\n'.join(lyrics)).split('\n')

        playing = True

        instance = vlc.Instance()

        if not instance:
            print_("Could not start the vlc player.")
            raise EnvironmentError("Could not start the vlc player.")

        self.player = instance.media_player_new()

        media = instance.media_new(resources.getSongDataPath(self.songs_fp, b64))
        self.player.set_media(media)

        self.player.play()
        resources.debug('Playback started.')

        time.sleep(0.5)

        total_time = round(self.player.get_length() / 1000)

        extra_lines = 7
        dc_cl = resources.ESCAPE_CODE + f"[38;2;{dc[0]};{dc[1]};{dc[2]}m"
        dc_bg_cl = resources.ESCAPE_CODE + f"[48;2;{dc[0]};{dc[1]};{dc[2]}m"

        mv_back = 4
        pad = 3

        original_lyrics = lyrics

        lyrics = original_lyrics
        wrapped_lyrics = []
        for lyric in lyrics:
            lyric = lyric.strip()

            if len(lyric) > self.lyrics_width:
                wrapped_lyrics += [lyric[i:i+self.lyrics_width] for i in range(0, len(lyric), self.lyrics_width)]
            else:
                wrapped_lyrics.append(lyric.center(self.lyrics_width))

        lyrics = wrapped_lyrics

        lyrics_sec_start = 0
        lyrics_sec_height = self.height - extra_lines - 2
        length = self.lyrics_width + mv_back * 2 + ceil(w_p / 4) * 2

        title_sec_start = 0
        prev_scroll = 0

        lyrics += [' ' * (self.lyrics_width)] * lyrics_sec_height

        ascii_title = self.font.get(title.replace('\n', ' '))

        lyrics_color = resources.ESCAPE_CODE + "[38;5;255m" if sum(dc) / 3 <= 127.5 else resources.ESCAPE_CODE + "[38;5;0m"

        try:
            while (self.player.is_playing() or not playing):
                if self.ensureResize():
                    w_p, h_p = self.small_img
                    playlist_cover = resources.coverArtToText(f'{self.main_fp}/{fp.PLAYLIST}.{self.cover_ext}', density, w_p, h_p)

                    w_c, h_c = self.giant_img
                    dc = self.dcs[b64]
                    cover_art = resources.coverArtToText(resources.getSongDataPath(self.cover_art_fp, b64, self.cover_ext), density, w_c, h_c)

                    lyrics = original_lyrics
                    wrapped_lyrics = []
                    for lyric in lyrics:
                        lyric = lyric.strip()

                        if len(lyric) > self.lyrics_width:
                            wrapped_lyrics += [lyric[i:i+self.lyrics_width] for i in range(0, len(lyric), self.lyrics_width)]
                        else:
                            wrapped_lyrics.append(lyric.center(self.lyrics_width))

                    lyrics = wrapped_lyrics

                    lyrics_sec_height = self.height - extra_lines
                    length = self.lyrics_width + mv_back * 2 + ceil(w_p / 4) * 2

                    lyrics += [' ' * (self.lyrics_width)] * lyrics_sec_height

                columns = []

                current_time_ms = self.player.get_time()
                current_time = round(current_time_ms / 1000)

                columns.append(list(map(
                    lambda x: x + ' ',
                    playlist_cover.splitlines())) + [' ' * (w_p + 1) for _ in range(self.height - len(playlist_cover.splitlines()))]
                )

                column = []
                column.append(f'{" " * pad}{dc_cl}◢{"■" * (length)}◣' + resources.ESCAPE_CODE + '[0m')
                column += list(map(
                        lambda x: f'{" " * pad}{dc_bg_cl}│{" " * ceil(w_p / 4)}{lyrics_color}' + x + ' ' * (mv_back * 2) + resources.ESCAPE_CODE + f'[0m{dc_bg_cl}{" " * ceil(w_p / 4)}│' + resources.ESCAPE_CODE + '[0m',
                        lyrics[lyrics_sec_start:lyrics_sec_start + lyrics_sec_height]
                ))
                column.append(f'{" " * pad}{dc_cl}◥{"■" * (length)}◤' + resources.ESCAPE_CODE + '[0m')
                column.append(' ' * (pad + length + 2))
                column.append(f'[b] ⏮  {"⏸" if playing else "▶"}  ⏭ [n]'.center(length - mv_back).ljust(pad + length + mv_back - 2))
                column.append(f'[space]'.center(length - mv_back) + ' ' * (mv_back * 2 + 3))
                column.append(f'{current_time//60}:{str(current_time%60).rjust(2, '0')[:2]} '.ljust(5) + (int(current_time / total_time * (length - mv_back)) * self.bar[0])[::-1].replace(self.bar[0], self.bar[1], 1)[::-1] + (((length - mv_back) - int(current_time / total_time  * (length - mv_back))) * self.bar[2]) + f' {total_time//60}:{str(total_time%60).rjust(2, '0')[:2]}'.rjust(5))

                columns.append(column)

                mod_ascii_title = []
                for ln in ascii_title.splitlines():
                    mod_ascii_title.append(ln[title_sec_start:title_sec_start + self.giant_img[0]])

                if self.shuffle and self.current_song < len(self.playing):
                    n_title = self.playing[self.current_song + 1][1]
                    n_artist = self.playing[self.current_song + 1][2]
                    n_b64 = self.playing[self.current_song + 1][3]

                    n_w, n_h = self.tiny_img
                    n_cover_art = resources.coverArtToText(f'{self.cover_art_fp}/{n_b64}.png', density, n_w, n_h)

                    max_len = self.giant_img[0] - 10 - n_w

                    if len(n_title) > max_len:
                        n_title = n_title[:max_len - 3] + '...'

                    if len(n_artist) > max_len:
                        n_artist = n_artist[:max_len - 3] + '...'

                    next = ['Next in queue:']
                    next.append(f'╭{"─" * (max_len + n_w + 4)}╮')

                    for c, ln in enumerate(n_cover_art.splitlines()):
                        next.append(f'{"│"}{ln}{" " * 4}{n_title.ljust(max_len) if c == 1 else ""}{(gray + n_artist.ljust(max_len) + resources.ESCAPE_CODE + "[0m") if c == 2 else " " * max_len if c != 1 else ""}' + resources.ESCAPE_CODE + f'[0m{"│"}')

                    next.append(f'╰{"─" * (max_len + n_w + 4)}╯')

                    next_pad = self.height - len(cover_art.splitlines() + ['', '', *mod_ascii_title, gray + artist + resources.ESCAPE_CODE + '[0m'] + next) - 5

                    column = cover_art.splitlines() + ['', '', *mod_ascii_title, gray + artist + resources.ESCAPE_CODE + '[0m'] + ['' for _ in range(next_pad)] + next

                else:
                    column = cover_art.splitlines() + ['', '', *mod_ascii_title, gray + artist + resources.ESCAPE_CODE + '[0m']

                columns.append(list(map(
                    lambda x: ' ' * (pad + 1) + x,
                    column + [' ' * (w_p + 1) for _ in range(self.height - len(column))]
                )))

                buffer = [''] + [list(group) for group in zip(*columns)]

                self.update_display(buffer)

                # Controls
                ch = resources.getch()

                if any([x == ch for x in resources.Keybinds.control.play]):
                    playing = not playing
                    self.player.pause()

                elif any([x == ch for x in resources.Keybinds.common.quit]):
                    resources.debug('Playback stopped (user quit).')
                    self.player.stop()
                    return

                elif any([x == ch for x in resources.Keybinds.common.back]):
                    self.player.stop()
                    self.list_view()
                    return

                elif any([x == ch for x in resources.Keybinds.navigation.up]):
                    lyrics_sec_start -= 1 if lyrics_sec_start > 0 else 0

                elif any([x == ch for x in resources.Keybinds.navigation.down]):
                    lyrics_sec_start += 1 if lyrics_sec_start + lyrics_sec_height + self.leftover_scroll < len(lyrics) else 0

                elif any([x == ch for x in resources.Keybinds.control.forward]):
                    if self.current_song + 1 < len(self.playing) - 1:
                        self.player.stop()
                        self.current_song += 1
                        self.play_view(self.playing[self.current_song])
                        return

                    else:
                        self.current_song = 0
                        self.playing = self.shuffleSongs(self.playing)

                elif any([x == ch for x in resources.Keybinds.control.backward]):
                    if self.current_song - 1 > 0:
                        self.player.stop()
                        self.current_song -= 1
                        self.play_view(self.playing[self.current_song])
                        return

                    else:
                        self.player.set_time(0)

                elif any([x == ch for x in resources.Keybinds.navigation.left]):
                    if (current_time_ms - self.fwd_amount) > 0:
                        self.player.set_time(current_time_ms - self.fwd_amount)

                    else:
                        self.player.set_time(0)

                elif any([x == ch for x in resources.Keybinds.navigation.right]):
                    if (current_time_ms + self.fwd_amount) / 1000 < total_time:
                        self.player.set_time(current_time_ms + self.fwd_amount)

                    else:
                        self.player.set_time(total_time*1000)

                elif any([x == ch for x in resources.Keybinds.common.delete]):
                    self._remove_song(self.playing[self.current_song])

                    if self.current_song + 1 < len(self.playing) - 1:
                        self.player.stop()
                        self.current_song += 1
                        self.play_view(self.playing[self.current_song])
                        return

                    else:
                        self.current_song = 0
                        self.playing = self.shuffleSongs(self.playing)

                if len(max(ascii_title.splitlines(), key=len)) > self.giant_img[0]:
                    if current_time_ms - prev_scroll > 100:
                        prev_scroll = current_time_ms
                        title_sec_start = title_sec_start + 1 if title_sec_start < len(max(ascii_title.splitlines(), key=len)) else 0

                time.sleep(self.interval)

        except KeyboardInterrupt:
            resources.debug('Playback stopped (keyboard interrupt).')

        self.player.stop()
        self.player.release()
        media.release()
        instance.release()
        self.handle_next()

    def exit(self):
        exit()
