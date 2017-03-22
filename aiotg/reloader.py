import sys
import os
import logging

from os import getcwd
from os.path import realpath

from aionotify import Watcher, Flags
from aionotify.base import Event
from paco import race

logger = logging.getLogger("aiotg")

async def setup_watcher(
        loop,
        path=realpath(getcwd()),
        alias="aiotg.watcher",
        flags=Flags.MODIFY | Flags.CREATE | Flags.DELETE,
        *args,
        **kwargs):

    """ Prepare watcher and set it up with the loop """

    # Create watcher
    watcher = Watcher()
    watcher.watch( alias=alias, flags=flags, path=path )

    # Setup watcher
    await watcher.setup( loop )
    return watcher

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

async def run_with_reloader( loop, coroutine, cleanup=lambda _:_, *args, **kwargs ):
    """ Run coroutine with reloader """

    watcher = await setup_watcher( loop, *args, **kwargs )
    logger.debug("Init watcher for file changes")

    # Run watcher and coroutine together
    result = race([await watcher.get_event(), await coroutine()])

    # Cleanup
    cleanup()
    watcher.close()

    # If change event, then reload
    if isinstance( result, Event ):
        logger.debug("Reloading")
        reload()
