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
parser.add_argument('--slow', action='store_true', help="Slow down the refresh rate to help get rid of flickering.")
parser.add_argument('--no-auto-resize', dest='no_auto_resize', action='store_true', help="Disable automatic ajustment to resizing of the terminal.")
parser.add_argument('--no-clear', dest='no_clear', action='store_true', help="Don't ever print \\ESC[2J (for debuging).")
parser.add_argument('--no-ascii', dest='no_ascii', action='store_true', help="Don't display ascii codes (for debuging).")
parser.add_argument('--no-print', dest='no_print', action='store_true', help="Don't print anything.")
parser.add_argument('--debug', default=0, type=int, help="Turn on debug mode with the level provided.")

try:
    args = parser.parse_args()
except argparse.ArgumentError:
    exit()

def main():
    if args.debug:
        resources.DEBUG = True
        resources.DEBUG_LEVEL = args.debug
        resources.DISABLE_CLEAR = True

    if args.no_ascii:
        resources.DISABLE_ASCII = True

    if args.no_print:
        resources.DISABLE_STDOUT = True

    if args.slow:
        resources.REDRAW_INTERVAL = 0.25

    if args.no_auto_resize:
        resources.NO_AUTO_RESIZE = True

    if args.shuffle:
        # Shuffle mode
        playlist = Playlist(args.name)
        playlist.shuffle = True
        songs = playlist.shuffleSongs(playlist.loadSongs())
        playlist.playing = songs

        playlist.handle_next()

        playing = playlist

    if args.no_clear:
        resources.DISABLE_CLEAR = True

    elif args.add:
        resources.display_info_mode = True
        playlist = Playlist(args.name, no_cover=True)
        resources._init_selenium_driver()

        playlist.add(args.add, resources.drivers[0], not args.no_lyrics)

        # Create playlist cover
        Playlist(args.name)

    elif args.sync_playlist:
        resources.display_info_mode = True
        playlist = Playlist(args.name, no_cover=True)

        playlist.sync(playlist.SyncType.spotify, args.sync_playlist)

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

        playing = playlist

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
