import logging

from pyinotify import ProcessEvent
import time
import os

logger = logging.getLogger('tsync')
logger.setLevel(logging.DEBUG)


class Filewatcher(ProcessEvent):
    """Find which files to sync."""

    def __init__(self, mfiles, rfiles, pulled_files):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulled_files = pulled_files

    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        if filename not in self.pulled_files:
            # Add a delay before adding the file to the mfiles set
            time.sleep(5)
            self.mfiles.add(filename, time.time())
            logger.info("Created file: %s", filename)
        else:
            self.pulled_files.remove(filename)

    def process_IN_DELETE(self, event):
        filename = os.path.join(event.path, event.name)
        self.rfiles.add(filename)
        try:
            self.mfiles.remove(filename)
        except KeyError:
            pass
        logger.info("Removed file: %s", filename)

    def process_IN_MODIFY(self, event):
        filename = os.path.join(event.path, event.name)
        if filename not in self.pulled_files:
            time.sleep(5)
            self.mfiles.add(filename, time.time())
            logger.info("Modified file: %s", filename)
        else:
            self.pulled_files.remove(filename)
