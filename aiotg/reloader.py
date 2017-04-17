import asyncio
import logging
import os
import sys

from os.path import realpath

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler as EventHandler
from watchdog.events import FileSystemEvent as Event

# Use a separate logger
logger = logging.getLogger("aiotg.reloader")


# Event handler class for watchdog
class Handler( EventHandler ):
    # Private
    _future_resolved = False

    # Common filetypes to watch
    patterns = ["*.py", "*.txt", "*.aiml", "*.json", "*.cfg", "*.xml", "*.html"]

    def __init__( self, *args, **kwargs ):

        # awaitable future to race on
        self.changed = asyncio.Future()

        # Continue init for EventHandler
        return super( Handler, self).__init__( *args, **kwargs )

    def on_any_event( self, event ):

        # Resolve future
        if isinstance( event, Event ) and not self._future_resolved:
            self.changed.set_result( event )
            self._future_resolved = True


def setup_watcher(
        loop,
        path=realpath(os.getcwd()),
        *args,
        **kwargs):

    """ Prepare watcher and set it up with the loop """

    # Create watcher
    handler = Handler()
    watcher = Observer()

    # Setup
    watcher.schedule( handler, path=path, recursive=True )
    watcher.start()

    logger.warning("Running with reloader. Should not be used in production")

    logger.debug("Init watcher for file changes in {}".format( path ))
    return watcher, handler


def reload():
    """ Reload process """
    try:
        # Reload and replace current process
        os.execv(sys.executable, [sys.executable] + sys.argv)

    except OSError:
        # Ugh, that failed
        # Try spawning a new process and exitj
        os.spawnv(
            os.P_NOWAIT,
            sys.executable,
            [sys.executable] + sys.argv,
        )
        os._exit(os.EX_OK)


async def run_with_reloader( loop, coroutine, cleanup=None, *args, **kwargs ):
    """ Run coroutine with reloader """

    watcher, handler = setup_watcher( loop, *args, **kwargs )

    # Run watcher and coroutine together
    done, pending = await asyncio.wait([coroutine, handler.changed],
                                       return_when=asyncio.FIRST_COMPLETED)

    # Cleanup
    cleanup and cleanup()
    watcher.stop()

    for fut in done:
        # If change event, then reload
        if isinstance(fut.result(), Event):
            logger.info("Reloading")
            reload()
