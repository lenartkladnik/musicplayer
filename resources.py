from math import floor
import curses
import os
import glob
import inspect
from PIL import Image
from unidecode import unidecode
from datetime import datetime as dt
import re
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium import webdriver
import subprocess
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import requests
import sys

# Globals
DEBUG = False
DEBUG_LEVEL = 0
DISABLE_STDOUT = False
LOG = []
LOG_PATH = ''
MINIMALIST_LEVEL = -1
MAX_PROC = 4
DISABLE_CLEAR = False
DISABLE_ASCII = False
ESCAPE_CODE = "\033"
SEARCH_STRING_LYRICS = True
REDRAW_INTERVAL = 0.05
NO_AUTO_RESIZE = False

successes = {'audio': 0, 'lyrics': 0, 'cover_art': 0}

display_info_mode = False

ansi_escape = re.compile(ESCAPE_CODE + r'\[[0-?]*[ -/]*[@-~]')

def print_(*values: object, sep: str | None = " ", end: str | None = "\n", file = None, flush = False) -> None:
    new_values = list(values)

    if DISABLE_ASCII:
        new_values = [ansi_escape.sub('', str(x)) for x in new_values]

    print(*new_values, sep=sep, end=end, file=file, flush=flush)

def debug(value: object, status: str = 'info', color: str = '', level: int = 0) -> None:
    """
    debug print_
    """

    if DEBUG and level <= DEBUG_LEVEL:
        stack = inspect.stack() # Inspect the stack to later find the function who called debug
        
        debug_msg = f'[{dt.now().strftime("%H:%M:%S")}] [{status.upper()}] [{stack[1].filename.split('/')[-1].split('\\')[-1]} -> {stack[1].function}] {value}'
        print_(color + debug_msg + ESCAPE_CODE + '[0m')
        LOG.append(debug_msg)

def display_info(value: object, status: str = 'info', color: str = '') -> None:
    if display_info_mode:
        print_(ESCAPE_CODE + f'[99999999D{color}[{status.upper()}] {value}' + ESCAPE_CODE + '[0m')

def _ensure_ublock_xpi() -> str:
    path = './ublock_origin.xpi'
    if not os.path.exists(path):
        ublock_url = "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest"

        response = requests.get(ublock_url)
        with open(path, "wb") as f:
            f.write(response.content)

    return path

firefox_options = None
drivers: list[webdriver.Firefox] = []

def _get_driver(geckodriver_path: str, firefox_options: Options) -> webdriver.Firefox:
    firefox_out = ""
    snap_out = ""
    try:
        firefox_out = subprocess.check_output(["which", "firefox"]).decode("utf-8")
        snap_out = subprocess.check_output(["snap", "list", "|", "grep", "firefox"]).decode("utf-8")
    except:
        pass

    if ("not found" in firefox_out or firefox_out.strip() == ""):
        print("No comatible browser was found on your device.")
        print("Please install one of: Mozilla Firefox")
        sys.exit()

    elif ("firefox" in snap_out):
        snap_firefox_bin = "/snap/firefox/current/usr/lib/firefox/firefox"
        snap_firefoxdriver_bin = "/snap/firefox/current/usr/lib/firefox/geckodriver"
        firefox_options.binary_location = snap_firefox_bin

        service = Service(executable_path=snap_firefoxdriver_bin)

        driver = webdriver.Firefox(
            service=service,
            options=firefox_options
        )

    else:
        try:
            driver = webdriver.Firefox(
                service=Service(geckodriver_path),
                options=firefox_options
            )

        except Exception:
            print_(geckodriver_path)
            os.remove(geckodriver_path)
            geckodriver_path = GeckoDriverManager().install()

            driver = webdriver.Firefox(
                service=Service(geckodriver_path),
                options=firefox_options
            )

    return driver


def _init_selenium_driver(instances: int = 1):
    global firefox_options
    global drivers

    display_info('Initializing main driver(s).')
    firefox_options = Options()

    if DEBUG_LEVEL < 2: firefox_options.add_argument("--headless")
    firefox_options.add_argument("--disable-gpu")
    firefox_options.add_argument("--no-sandbox")
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0"
    firefox_options.set_preference("general.useragent.override", user_agent)
    firefox_options.set_preference("dom.webdriver.enabled", False)
    firefox_options.set_preference("useAutomationExtension", False)
    firefox_options.set_preference("media.eme.enabled", True)
    firefox_options.set_preference("media.gmp-widevinecdm.enabled", True)
    firefox_options.set_preference("media.autoplay.default", 0)
    firefox_options.set_preference("media.gmp-manager.updateEnabled", True)
    firefox_options.set_preference("media.gmp-provider.enabled", True)
    firefox_options.set_preference("media.gmp-widevinecdm.visible", True)

    display_info('Initialized main options.')

    cache_dir = os.path.expanduser("~/.wdm/drivers/geckodriver/linux64")
    geckodriver_path = glob.glob(f"{cache_dir}/*/geckodriver")

    if geckodriver_path:
        geckodriver_path = geckodriver_path[0]
    else:
        geckodriver_path = GeckoDriverManager().install()

    for _ in range(instances):
        driver = _get_driver(geckodriver_path, firefox_options)
        path = _ensure_ublock_xpi()
        driver.install_addon(os.path.abspath(path))

        driver.get('https://www.youtube.com/')
        time.sleep(1)

        actions = ActionChains(driver)

        for i in range(5):
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.3)

        time.sleep(0.2)
        actions.send_keys(Keys.ENTER).perform()

        drivers.append(driver)
        display_info(f'Added driver number {len(drivers)}.')

    display_info('Initialized main driver(s).')

class Key:
    class common:
        escape: str = 'ESC'
        command: str = ':'
        delete: str = 'DEL'

    class navigation:
        up: str = 'UP_ARROW'
        down: str = 'DOWN_ARROW'
        left: str = 'LEFT_ARROW'
        right: str = 'RIGHT_ARROW'

class Keybinds:
    class common:
        quit: list[str] = ['q']
        back: list[str] = ['r']
        shuffle: list[str] = ['e']
        search: list[str] =  ['f', '/']
        delete: list[str] = [Key.common.delete]
     
    class control:
        play: list[str] = ['p', ' ']
        enter: list[str] = ['\n']
        forward: list[str] = ['n']
        backward: list[str] = ['b']

    class navigation:
        up: list[str] = ['w', Key.navigation.up, 'k']
        down: list[str] = ['s', Key.navigation.down, 'j']
        left: list[str] = ['a', Key.navigation.left, 'l']
        right: list[str] = ['d', Key.navigation.right, 'h']

    extra_actions: list[str] = [':', '/']

class Keybind:
    class goto:
        top: str = 'gg'
        bottom: str = 'gb'

def getch(blocking: bool = False) -> str | None:
    """
    Returns the key being pressed (as a string) or None if no key is pressed.
    Prevents input from being echoed to the screen and clears the input buffer.
    """
    # Initialize curses
    stdscr = curses.initscr()
    curses.noecho()  # Prevent input from being echoed to the screen
    curses.cbreak()  # Disable line buffering
    stdscr.nodelay(not blocking)  # Make getch() non-blocking or blocking
    stdscr.keypad(True)  # Enable special keys (e.g., arrow keys)

    try:
        key = stdscr.getch()
        if key != -1:

            if key == 27:
                next_key = stdscr.getch()
                if next_key == -1:
                    return Key.common.escape
                elif next_key == 91:
                    next_key = stdscr.getch()
                    if next_key == 65:
                        return Key.navigation.up
                    elif next_key == 66:
                        return Key.navigation.down
                    elif next_key == 67:
                        return Key.navigation.right
                    elif next_key == 68:
                        return Key.navigation.left
                    elif next_key == 51:
                        next_key = stdscr.getch()
                        if next_key == 126:
                            return Key.common.delete
            
            else:
                return chr(key)
        return None
    finally:
        # Clean up curses
        curses.flushinp()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

ansi_escape = re.compile(ESCAPE_CODE + r'\[[0-9;]*[a-zA-Z]')

def db_print_(*values: str, sep: str = " ", end: str | None = "\n", file: str | None = None, flush: bool = False, no_clear: bool = False):
    """
    print_s values but with some added functionality
    """

    if not DISABLE_STDOUT:
        if not no_clear:
            print_("\r" + ESCAPE_CODE + "[0K", end="", flush=flush) # Add \ESC[0K to start of values to clear any weird artifacts in front of the string
        
        if MINIMALIST_LEVEL == 2:
            # Remove all ansi escape codes
            values = tuple([ansi_escape.sub('', str(value)) for value in values])
        
        print_(*values, end=end, sep=sep, file=file, flush=flush)
        
        if LOG_PATH:
            LOG.append(sep.join(values))

def cleanTitleArtist(s: str) -> str:
    debug(f'Stripping: {s}')

    s = unidecode(s)
    s = s.lower().replace("'", '').replace('.', '')
    s = s.split(' - ')[0]

    p = False
    n_s = ''
    for i in s:
        if p:
            if i == ')':
                p = False
            continue

        if i == '(':
            p = True
            continue

        n_s += i

    s = n_s

    s = s.split(' feat')[0]
    s = s.split(' ft')[0]

    s = replaceNonAlphaNum(s, '-')

    debug(f'Stripped: {s}')

    return s

def stripNonAlphaNum(s: str) -> str:
    """
    Removes non alpha numerical characters (excluding space) from string
    """
    
    n_s = ''
    for i in s:
        n_s += i if i.isalnum() or i == ' ' else ''

    return n_s

def replaceNonAlphaNum(s: str, n: str) -> str:
    """
    Replaces non alpha numerical characters (excluding space) in string
    """
    
    n_s = ''
    for i in s:
        if i.isalnum() or i == ' ':
            n_s += i

        else:
            n_s += n

    return n_s

def reset_screen():
    if not DISABLE_CLEAR:
        print_(ESCAPE_CODE + '[2J' + ESCAPE_CODE + '[H', end='')

def matching(s1: str, s2: str, split: str = ' ', diff: int = 2, instant_match: bool = False, ln_match: bool = False) -> bool:
    """
    More tolerant matching function
    used mainly for searching in this program
    """

    s1 = stripNonAlphaNum(s1).lower()
    s2 = stripNonAlphaNum(s2).lower()
    debug(f'Checking for match between {s1=}, {s2=}')
    if (s1 in s2) or (s2 in s1) and (not ln_match):
        debug('Strings include each other.')
        return True
    
    matches = 0
    s1_split = s1.strip().split(split)
    s2_split = s2.strip().split(split)
    if len(s1_split) != len(s2_split):
        debug("Length doesn't match")
        return False
    
    for c in range(len(min(s1_split, s2_split, key=len))):
        i = s1_split[c]
        j = s2_split[c]
        debug(f'{i=}, {j=}', level=1)
        debug(f'Char diff: {(len(set(i).difference(set(j))) + len(set(j).difference(set(i))))}', level=1)
        debug(f'Len diff: {abs(len(i) - len(j))}')
        if (len(set(i).difference(set(j))) + len(set(j).difference(set(i)))) <= diff and abs(len(i) - len(j)) < diff:
            if instant_match:
                debug('Match found.')
                return True

            debug(f'New matching section found, now up to {matches}.')

            matches += 1
    
    if matches >= diff:
        debug('Match found.')
        return True
    
    debug('Not a match.')
    return False

def coverImgToText(image: Image, density: dict, w: int, h: int) -> str:
    """
    Convert an image to ascii art with ansi color codes
    """

    debug('Getting ascii cover art from image.')
    im = image
    debug('Opened image.')
        
    im = im.resize((w, h), Image.Resampling.LANCZOS) # Resize to 2x width since text characters are about 2x taller than they are wide
    debug('Resized image.')
    mono = im.convert('L') # Get a clone of the image in monochrome (for the density)
    debug('Converted image clone to monochrome.')
    im = im.convert('RGB') # Ensure the image is in RGB
    debug('Converted image to RGB.')
    
    img = []
    tmp = ''
    
    for y in range(im.height):
        for x in range(im.width):
            mono_pixel = mono.getpixel((x, y))
            r, g, b = im.getpixel((x, y))
            
            density_char, _ = min(density.items(), key=lambda i: abs(mono_pixel - i[1])) # The character from the density map
            tmp += ESCAPE_CODE + f"[1m" + ESCAPE_CODE + f"[38;2;{r};{g};{b}m{density_char}" + ESCAPE_CODE + "[0m" # Combine the RGB and density character (this is one character)
        
        img.append(tmp)
        debug(f'Converted row {y + 1} to ascii.', level=1)
        tmp = ''
    
    debug('Got ascii cover art from image.')

    return '\n'.join(img)

def coverArtToText(fp: str, density: dict, w: int, h: int) -> str:
    if os.path.exists(fp):
        im = Image.open(fp)

        return coverImgToText(im, density=density, w=w, h=h)
    
    display_info('Cover art not found.')
    return '\n'.join([list(density.keys())[0] * w] * h)

def cleanup():
    debug('Started cleanup.')
    if drivers:
        for driver in drivers:
            driver.quit()

    if not DISABLE_CLEAR:
        os.system('clear')

    debug('Cleanup successful.')

class progressBar:
    def __init__(self, total: int, length: int, text: str, fill: str = '=', blank: str = '-'):
        self.total = total
        self.length = length
        self.chunk = floor(self.length / self.total)
        self.fill = fill
        self.blank = blank
        self.full = 0
        self.text = text

    def start(self):
        print_(f'{self.text} {self.fill * self.full}{self.blank * (self.total - self.full)} [{self.full}/{self.total}]')

    def next(self):
        self.full += 1
        print_(f'{self.text} {self.fill * self.full}{self.blank * (self.total - self.full)} [{self.full}/{self.total}]')

    def keep(self):
        print_(f'{self.text} {self.fill * self.full}{self.blank * (self.total - self.full)} [{self.full}/{self.total}]')

    def discard(self):
        print_(ESCAPE_CODE + '[2K', end='')

class FontError(Exception):...

class Figlet: # Old bad code don't bother
    def __init__(self, font_name: str, download: bool = True) -> None:
        """
        font_name - the font name (Eg. font_name="big.flf" or font_name="big")
        If download is True the program will try to download the font from 'figlet.org/fonts'.
        """
        if not font_name.endswith(".flf"): font_name += ".flf"

        self.font_name = font_name

        if download:
            if not os.path.exists(font_name):
                with open(font_name, "w+") as f:
                    font_contents = subprocess.check_output(f'curl "http://www.figlet.org/fonts/{font_name}"', shell=True).decode()
                    f.write(font_contents)

        with open(font_name, encoding="utf-8") as f:
            self.font = f.read()
        if self.font.startswith("<!DOCTYPE"):
            os.remove(font_name)
            raise FontError(f"No font named '{font_name}' could be found.")

        self.width = 0
    
    def _check_width(self, string: str, width: int) -> bool:
        if self.width + len(string.split("\n")[0]) > width:
            self.width = 0
            return False
        
        else:
            self.width += len(string.split("\n")[0])
            return True

    def _parse(self, text: str, indicator: str, space: str, padding: int, width: int) -> list[list[str]]:
        vars = self.font.split("\n")[0].split("flf2a")[1].split(" ")
        blank = vars[0]
        height = vars[1]

        for c, line in enumerate(self.font.split("\n")):
            if line.replace(blank, "").replace(indicator, "").replace(" ", "") == "" and indicator in line and blank in line:
                contents = self.font.split("\n")[c:]
                break

        chars_list: list[list[str]] = []
        char_line: list[str] = []

        for chr in text:
            chars: list[str] = []
            c = []

            for line in contents:
                if indicator * 2 in line:
                    c.append(space[0] * padding + line[1:-2])
                    chars.append("\n".join(c))
                    c = []

                else:
                    c.append(space[0] * padding + line[1:-1])

            char = chars[ord(chr) - 32]

            if char.replace(" ", "").replace(blank, "").replace("\n", "") == "":
                char_line.append("\n".join([space] * int(height)))

            else:
                char_line.append(char.replace(blank, " "))

        if char_line:
            chars_list.append(char_line)

        return chars_list
    
    def get(self, text: str, indicator: str = "@", space: str = " " * 3, padding: int = 0, width: int = 120) -> str:
        """
        Return text in a given figlet font wrapped to width.\n
        """
        lines = []
        try:
            parsed = self._parse(text, indicator, space, padding, width)
        except:
            raise FontError(f"The font file '{self.font_name}' seems to be corrupt.")

        for line in parsed:
            lines.append(self._next_vals(*line))
        
        return "\n".join(lines)
    
    def _next_vals(self, *values: str, padding: int = 0) -> str:
        values = list(map(lambda t: t + " " * padding, values))
        values[-1] = str(values[-1]).back_replace(" " * padding, "") if padding != 0 else values[-1]
        lines = [arg.split("\n") for arg in values]
        max_lines = max(len(line) for line in lines)

        for line in lines:
            while len(line) < max_lines:
                line.append(" " * padding)

        display_lines = ["".join(parts) for parts in zip(*lines)]
            
        display = "\n".join(display_lines)
            
        return display
    
def exception(message: str):
    print_(ESCAPE_CODE + f'[38;5;203m{message}' + ESCAPE_CODE + '[0m')
    cleanup()
    sys.exit(1)

def exit() -> None:
    cleanup()
    sys.exit(1)

class Spotify:
    def get_songs(self, playlist_id: str):
        songs = []

        if ("open.spotify.com" in playlist_id):
            playlist_id = playlist_id.split("playlist/")[1]

        playlist_url = f'https://mpbe.kladnik.cc/playlist/{playlist_id}'

        response = requests.get(playlist_url)
        playlist_data = response.json()

        for item in playlist_data['items']:
            track = item['track']
            track_name = track['name']
            artists = ', '.join([artist['name'] for artist in track['artists']])
            songs.append([track_name, artists])

        return songs

def getSongDataPath(dir_path: str, song_b64: str, ext: str = '*') -> str:
    files = glob.glob(os.path.join(dir_path, f'{song_b64}.{ext}'))

    if files:
        return files[0]
    
    return ""

def existsSongData(dir_path: str, song_b64: str, ext: str = '*') -> bool:
    data = getSongDataPath(dir_path=dir_path, song_b64=song_b64, ext=ext)
    
    return data and os.path.exists(data)
    
