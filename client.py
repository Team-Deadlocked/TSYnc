import logging
import sxmlr
from pyinotify import WatchManager, ProcessEvent
import pyinotify
import subprocess
import time
import threading
import os
from Parent import Base
from persistence import FileData, FilesPersistentSet

logger = logging.getLogger('TSYnc')


# Find which files to sync
class PTmp(ProcessEvent):
    """Find which files to sync"""

    def __init__(self, mfiles, rfiles, pulledfiles):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulled_files = pulledfiles

    def process_IN_CREATE(self, event):
        filename = os.path.join(event.path, event.name)
        if not self.pulled_files.__contains__(filename):
            self.mfiles.add(filename, time.time())
            logger.info("Created file: %s", filename)
        else:
            pass
            self.pulled_files.remove(filename)

    def process_IN_DELETE(self, event):
        filename = os.path.join(event.path, event.name)
        self.rfiles.add(filename)
        try:
            self.mfiles.remove(filename)
        except KeyError:
            pass
        logger.info("Removed file: %s", filename)

    # def process_IN_MODIFY(self, event):
    #     filename = os.path.join(event.path, event.name)
    #     if not self.pulled_files.__contains__(filename):
    #         self.mfiles.add(filename, time.time())
    #         logger.info("Modified file: %s", filename)
    #     else:
    #         self.pulled_files.remove(filename)

    def process_IN_MODIFY(self, event):
        filename = os.path.join(event.path, event.name)
        current_time = time.time()
        if not self.pulled_files.__contains__(filename):  # Check if the file is in pulled_files
            file_exists = False
            for filedata in self.mfiles.list():
                if filedata.name == filename:
                    file_exists = True
                    last_modified_time = filedata.time
                    break
            if file_exists and current_time - last_modified_time > 5:
                self.mfiles.add(filename, current_time)
                logger.info("Modified file: %s", filename)
        else:
            self.pulled_files.remove(filename)


class Client(Base):
    """Client class"""

    def __init__(self, role, ip, port, uname, watch_dirs, server):
        super(Client, self).__init__(role, ip, port, uname, watch_dirs)
        self.server = server
        self.mfiles = FilesPersistentSet(pkl_filename='client.pkl')  # set() #set of modified files
        self.rfiles = set()  # set of removed files
        self.pulled_files = set()
        self.server_available = True

    def push_file(self, filename, dest_file, dest_uname, dest_ip):
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, dest_file)])
        push_status = proc.wait()
        logger.debug("returned status %s", push_status)
        return push_status

    def pull_file(self, filename, source_uname, source_ip):
        """pull file 'filename' from the source"""
        my_file = Base.get_dest_path(filename, self.username)
        self.pulled_files.add(my_file)
        proc = subprocess.Popen(['scp', "%s@%s:%s" % (source_uname, source_ip, filename), my_file])
        return_status = proc.wait()
        logger.debug("returned status %s", return_status)

    def get_public_key(self):
        """Return public key of this client"""
        pubkey = None
        pubkey_dirname = os.path.join("/home", self.username, ".ssh")
        logger.debug("public key directory %s", pubkey_dirname)
        for tuple in os.walk(pubkey_dirname):
            dirname, dirnames, filenames = tuple
            break
        logger.debug("public key dir files %s", filenames)
        for filename in filenames:

            if '.pub' in filename:
                pubkey_filepath = os.path.join(dirname, filename)
                logger.debug("public key file %s", pubkey_filepath)
                pubkey = open(pubkey_filepath, 'r').readline()
                logger.debug("public key %s", pubkey)

        return pubkey

    def find_modified(self):
        for directory in self.watch_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    last_modified = self.mfiles.get_modified_timestamp()  # Get the timestamp
                    if last_modified is not None and mtime > last_modified:
                        logger.debug("File %s modified", file_path)
                        self.mfiles.add(file_path, mtime)

    def sync_files(self):
        """Sync all the files present in the mfiles set and push this set"""
        mfiles = self.mfiles
        while True:
            try:
                time.sleep(10)
                for filedata in mfiles.list():
                    filename = filedata.name
                    logger.info("push filedata object to server %s", filedata)
                    server_uname, server_ip, server_port = self.server
                    dest_file = sxmlr.req_push_file(server_ip, server_port, filedata, self.username, self.ip,
                                                   self.port)
                    logger.debug("destination file name %s", dest_file)
                    if dest_file is None:
                        break
                    push_status = self.push_file(filename, dest_file, server_uname, server_ip)
                    if (push_status < 0):
                        break
                    rpc_status = sxmlr.ack_push_file(server_ip, server_port, dest_file, self.username, self.ip,
                                                    self.port)

                    if rpc_status is None:
                        break
                    mfiles.remove(filename)
                self.mfiles.update_modified_timestamp()
            except KeyboardInterrupt:
                break

    def watch_files(self):
        """keep a watch on files present in sync directories"""
        try:
            wm = WatchManager()
            # watched events
            mask = pyinotify.IN_DELETE | pyinotify.IN_CREATE | pyinotify.IN_MODIFY
            notifier = pyinotify.Notifier(wm, PTmp(self.mfiles, self.rfiles, self.pulled_files))

            logger.debug("watched dir %s", self.watch_dirs)
            for watch_dir in self.watch_dirs:
                wm.add_watch(os.path.expanduser(watch_dir), mask, rec=False, auto_add=True)
            while True:
                try:
                    time.sleep(5)
                    notifier.process_events()
                    if notifier.check_events():
                        notifier.read_events()
                except KeyboardInterrupt:
                    notifier.stop()
                    break
        except Exception as e:
            logger.error("Exception occurred in watch_files: %s", str(e))
            raise

    def start_watch_thread(self):
        """Start threads to find modified files """
        watch_thread = threading.Thread(target=self.watch_files)
        watch_thread.start()
        logger.info("Thread 'watchfiles' started ")

    def mark_presence(self):
        server_uname, server_ip, server_port = self.server
        logger.debug("client call to mark available to the server")
        sxmlr.mark_presence(server_ip, server_port, self.ip, self.port)
        logger.debug("find modified files")

    def activate(self):
        """ Activate Client Node """
        super(Client, self).activate()
        self.start_watch_thread()
        self.mark_presence()
        self.find_modified()