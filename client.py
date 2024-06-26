import logging
import sxmlr
from pyinotify import WatchManager, Notifier, EventsCodes
import subprocess
import time
import threading
import os
from base import Base
from filewatcher import Filewatcher
from filepersistentset import FilesPersistentSet
from timekeeper import TimeKeeper

logger = logging.getLogger('tsync')
logger.setLevel(logging.DEBUG)


class Client(Base):
    """Client class."""

    def __init__(self, role, ip, port, uname, watch_dirs, server_details):
        super(Client, self).__init__(role, ip, port, uname, watch_dirs)
        self.server_uname, self.server_ip, self.server_port = server_details
        self.mfiles = FilesPersistentSet(pkl_filename='client.pkl')
        self.rfiles = set()
        self.pulled_files = set()
        self.server_available = True

        # Ensure client-specific methods are registered if not in Base
        self.server.funcs.update({
            'get_public_key': self.get_public_key,
            'pull_file': self.pull_file,
            'push_file': self.push_file
        })

    def push_file(self, filename, dest_file, dest_uname, dest_ip):
        proc = subprocess.Popen(['scp', filename, f"{dest_uname}@{dest_ip}:{dest_file}"])
        push_status = proc.wait()
        logger.debug("Returned status %s", push_status)
        return push_status

    def pull_file(self, filename, source_uname, source_ip):
        """Pull file 'filename' from the source."""
        my_file = filename.replace("/.tsync", "")
        my_file = Base.get_dest_path(my_file, self.username, self.role)
        print("my file is ", my_file)
        self.pulled_files.add(my_file)
        proc = subprocess.Popen(['scp', f"{source_uname}@{source_ip}:{filename}", my_file])
        return_status = proc.wait()
        logger.debug("logging from pull_file of client on filename %s", my_file)
        logger.debug("Returned status %s", return_status)

    def get_public_key(self):
        """Return public key of this client."""
        pubkey_dirname = os.path.join("/home", self.username, ".ssh")
        logger.debug("Public key directory %s", pubkey_dirname)

        pubkey = None
        for root, _, filenames in os.walk(pubkey_dirname):
            for filename in filenames:
                if filename.endswith('.pub'):
                    pubkey_filepath = os.path.join(root, filename)
                    logger.debug("Public key file %s", pubkey_filepath)
                    with open(pubkey_filepath, 'r') as pubkey_file:
                        pubkey = pubkey_file.readline().strip()
                        logger.debug("Public key %s", pubkey)
                    break
            if pubkey:
                break

        return pubkey

    def find_modified(self):
        """Find and mark modified files."""
        last_sync_time = TimeKeeper.get_time()
        for directory in self.watch_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    print("mtime is ", mtime, "last sync time is ", last_sync_time)
                    print("mtime - last_sync_time", mtime - last_sync_time)
                    if mtime - last_sync_time > 20 and file_path not in self.pulled_files:
                        print("I am the stupid find modifid", file)
                        logger.debug("File %s modified in stupid find_modified", file_path)
                        self.mfiles.add(file_path, mtime)

    def sync_files(self):
        """Sync all the files present in the mfiles set and push this set."""
        while True:
            try:
                time.sleep(10)
                for filedata in self.mfiles.list():
                    filename = filedata.name
                    logger.info("Attempting to push file: %s", filename)
                    dest_file = sxmlr.req_push_file(self.server_ip, self.server_port, filedata, self.username, self.ip,
                                                    self.port)
                    logger.debug("Destination file path received: %s", dest_file)
                    if dest_file is None:
                        logger.error("Failed to get destination file path for %s", filename)
                        break
                    push_status = self.push_file(filename, dest_file, self.server_uname, self.server_ip)
                    logger.debug("Push file status for %s: %s", filename, push_status)
                    if push_status < 0:
                        logger.error("Failed to push file %s", filename)
                        break
                    rpc_status = sxmlr.ack_push_file(self.server_ip, self.server_port, dest_file, self.username,
                                                     self.ip, self.port)
                    logger.debug("Acknowledgement status for file %s: %s", dest_file, rpc_status)
                    if rpc_status is None:
                        logger.error("Failed to get acknowledgement for file %s", dest_file)
                        break
                    self.mfiles.remove(filename)
                    logger.info("Successfully synced and removed file: %s", filename)
                self.mfiles.update_modified_timestamp()
                TimeKeeper.update_time()
            except KeyboardInterrupt:
                break

    def watch_files(self):
        """Keep a watch on files present in sync directories."""
        try:
            wm = WatchManager()
            mask = EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CREATE'] | \
                   EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_DELETE'] | \
                   EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_MODIFY']
            notifier = Notifier(wm, Filewatcher(self.mfiles, self.rfiles, self.pulled_files))

            logger.debug("Watched directories %s", self.watch_dirs)
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
        """Start threads to find modified files."""
        watch_thread = threading.Thread(target=self.watch_files)
        watch_thread.start()
        logger.info("Thread 'watch_files' started")

    def mark_presence(self):
        """Mark this client as available to the server."""
        logger.debug("Client call to mark available to the server")
        sxmlr.mark_presence(self.server_ip, self.server_port, self.ip, self.port)
        logger.debug("Find modified files")

    def activate(self):
        """Activate Client Node."""
        super(Client, self).activate()
        self.start_watch_thread()
        self.mark_presence()
        self.find_modified()
