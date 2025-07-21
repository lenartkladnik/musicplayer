# MusicPlayer
Play music right from the terminal.

## Usage
```
usage: musicplayer.py [-h] [-Rp] [-Rm REMOVE] [-s] [-Sp SYNC_PLAYLIST] [-A ADD] [-nl] [--no-clear] [--no-ascii] [--debug DEBUG] name

A music player for the terminal.

positional arguments:
  name                  Name of the playlist.

options:
  -h, --help            show this help message and exit
  -Rp, --remove-playlist
                        Remove the playlist.
  -Rm, --remove REMOVE  Remove a song from the playlist.
  -s, --shuffle         Automatically start shuffle mode.
  -Sp, --sync-playlist SYNC_PLAYLIST
                        Sync playlist, provide the spotify playlist ID or URL.
  -A, --add ADD         Add song by title and artist(s), provide "title by (comma sep.) artist(s)".
  -nl, --no-lyrics      Don't add lyrics.
  --no-clear            Don't ever print \x1b[2J (for debuging).
  --no-ascii            Don't display ascii codes (for debuging).
  --debug DEBUG         Turn on debug mode with the level provided.
```
```
```
```
```


