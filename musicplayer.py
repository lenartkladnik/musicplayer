from playlist import Playlist
import resources
from resources import print_
import argparse
import traceback

parser = argparse.ArgumentParser(description='A music player for the terminal.')
parser.add_argument('name', help='Name of the playlist.')
parser.add_argument('-Rp', '--remove-playlist', dest='remove_playlist', action='store_true', help='Remove the playlist.')
parser.add_argument('-Rm', '--remove', help='Remove a song from the playlist.')
parser.add_argument('-s', '--shuffle', action='store_true', help='Automatically start shuffle mode.')
parser.add_argument('-Sp', '--sync-playlist', dest='sync_playlist', help="Sync playlist, provide the spotify playlist ID or URL.")
parser.add_argument('-A', '--add', help='Add song by title and artist(s), provide "title by (comma sep.) artist(s)".')
parser.add_argument('-nl', '--no-lyrics', dest='no_lyrics', action='store_true', help="Don't add lyrics.")
parser.add_argument('--no-clear', dest='no_clear', action='store_true', help="Don't ever print \\x1b[2J (for debuging).")
parser.add_argument('--no-ascii', dest='no_ascii', action='store_true', help="Don't display ascii codes (for debuging).")
# parser.add_argument('-i', '--instances', dest='instances', type=int, default=1, help="Set the number of selenium instances used for the downloader.")
parser.add_argument('--debug', default=0, type=int, help="Turn on debug mode with the level provided.")

try:
    args = parser.parse_args()
except argparse.ArgumentError:
    exit()

def main():
    # instances = args.instances
    instances = 1

    if args.debug:
        resources.DEBUG = True
        resources.DEBUG_LEVEL = args.debug
        resources.DISABLE_CLEAR = True

    if args.no_ascii:
        resources.DISABLE_ASCII = True

    if args.shuffle:
        # Shuffle mode
        playlist = Playlist(args.name)
        playlist.shuffle = True
        playlist.songs = playlist.shuffleSongs(playlist.songs)
        playlist.handle_next(playlist.songs)

    if args.no_clear:
        resources.DISABLE_CLEAR = True

    elif args.add:
        resources.display_info_mode = True
        playlist = Playlist(args.name, no_cover=True)
        
        resources._init_selenium_driver()

        if ' by ' in args.add:
            title, artists = args.add.split(' by ', 1)

        elif ' , ' in args.add:
            title, artists = args.add.split(' , ', 1)

        elif ',' in args.add:
            title, artists = args.add.split(',', 1)

        else:
            title, artists = args.add.split(' ', 1)

        playlist.add(title, artists, resources.drivers[0], not args.no_lyrics)

        # Create playlist cover
        Playlist(args.name)
        
    elif args.sync_playlist:
        resources.display_info_mode = True
        playlist = Playlist(args.name, no_cover=True)

        resources._init_selenium_driver(instances)
        resources._init_sp_selenium_driver()

        spotify = resources.Spotify()

        total = 0
        
        for songs in spotify.get_songs(args.sync_playlist):
            if songs:
                playlist.add_batch(list(map(lambda x: x[0], songs)), list(map(lambda x: x[1], songs)), instances, not args.no_lyrics)

            total += len(songs)

        # Create playlist cover
        Playlist(args.name)

        print_('\x1b[38;5;40mDone.\x1b[0m')
        print_(f'Got {resources.successes['audio']}/{total} ({round(resources.successes['audio'] / total, 2) * 100}%) audio files.')
        print_(f'Got {resources.successes['lyrics']}/{total} ({round(resources.successes['lyrics'] / total, 2) * 100}%) lyrics.')
        print_(f'Got {resources.successes['cover_art']}/{total} ({round(resources.successes['cover_art'] / total, 2) * 100}%) cover arts.')
        print_()

    elif args.remove:
        playlist = Playlist(args.name)
        playlist.remove_song(args.remove)

    elif args.remove_playlist:
        playlist = Playlist(args.name)
        if input(f"Are you sure you want to remove the playlist '{args.name}'? [y/N] ").lower() == 'y':
            playlist.remove_playlist()
            print_('Removed playlist.')

    else:
        # Standard
        resources.reset_screen()

        resources.display_info_mode = True

        playlist = Playlist(args.name)
        playlist.list_view()

        resources.reset_screen()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        resources.debug('Received a keyboard interrupt.')
        resources.debug(traceback.format_exc())
        print()
        
    except Exception as e:
        resources.debug('Got exception in main:')
        resources.debug(traceback.format_exc())
        
    finally:
        resources.cleanup()
