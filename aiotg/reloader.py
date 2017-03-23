import asyncio
import logging
import os
import sys

from os.path import realpath

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler as EventHandler
from watchdog.events import FileSystemEvent as Event
from paco import race

logger = logging.getLogger("aiotg")


# Event handler class for watchdog
class Handler( EventHandler ):
    _future_resolved = False

    def __init__( self, *args, **kwargs ):

        # awaitable future to race on
        self.changed = asyncio.Future()
        asyncio.ensure_future( self.changed )

        # Continue init for EventHandler
        return super( Handler, self).__init__( *args, **kwargs )

    def on_any_event( self, event ):

        # Resolve future
        if isinstance( event, Event ) and not self._future_resolved:
            self.changed.set_result( event )
            self._future_resolved = True

    # Coroutine for racing
    async def change( self ):
        return await self.changed


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

    print("Running with reloader. Should not be used in production")

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

    # Set logging level (reloader should only run in dev environment)
    logger.setLevel( logging.DEBUG )

    watcher, handler = setup_watcher( loop, *args, **kwargs )

    # Run watcher and coroutine together
    result = await race([coroutine, handler.change])

    # Cleanup
    cleanup and cleanup()
    watcher.stop()

    # If change event, then reload
    if isinstance( result, Event ):
        logger.debug("Reloading")
        reload()
