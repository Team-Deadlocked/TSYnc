import logging
import sxmlr
from pyinotify import WatchManager, Notifier, ProcessEvent, EventsCodes
import subprocess
import time
import threading
import os
from parent import Base
from persistence import FileData, FilesPersistentSet

logger = logging.getLogger('syncIt')
logger.setLevel(logging.DEBUG)

class PTmp(ProcessEvent):
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
        current_time = time.time()
        if filename not in self.pulled_files:
            file_exists = False
            for filedata in self.mfiles.list():
                if filedata.name == filename:
                    file_exists = True
                    last_modified_time = filedata.time
                    break
            if file_exists and current_time - last_modified_time > 150:
                self.mfiles.add(filename, current_time)
                logger.info("Modified file: %s", filename)
        else:
            self.pulled_files.remove(filename)

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
            'pull_file': self.pull_file
        })

    def push_file(self, filename, dest_file, dest_uname, dest_ip):
        proc = subprocess.Popen(['scp', filename, f"{dest_uname}@{dest_ip}:{dest_file}"])
        push_status = proc.wait()
        logger.debug("Returned status %s", push_status)
        return push_status

    def pull_file(self, filename, source_uname, source_ip):
        """Pull file 'filename' from the source."""
        my_file = Base.get_dest_path(filename, self.username)
        self.pulled_files.add(my_file)
        proc = subprocess.Popen(['scp', f"{source_uname}@{source_ip}:{filename}", my_file])
        return_status = proc.wait()
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
        for directory in self.watch_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    if self.mfiles.get(file_path) is None or self.mfiles.get(file_path).time < mtime:
                        logger.debug("File %s modified", file_path)
                        self.mfiles.add(file_path, mtime)

    def sync_files(self):
        """Sync all the files present in the mfiles set and push this set."""
        while True:
            try:
                time.sleep(10)
                for filedata in self.mfiles.list():
                    filename = filedata.name
                    logger.info("Push filedata object to server %s", filedata)
                    dest_file = sxmlr.req_push_file(self.server_ip, self.server_port, filedata, self.username, self.ip, self.port)
                    logger.debug("Destination file name %s", dest_file)
                    if dest_file is None:
                        break
                    push_status = self.push_file(filename, dest_file, self.server_uname, self.server_ip)
                    if push_status < 0:
                        break
                    rpc_status = sxmlr.ack_push_file(self.server_ip, self.server_port, dest_file, self.username, self.ip, self.port)
                    if rpc_status is None:
                        break
                    self.mfiles.remove(filename)
                self.mfiles.update_modified_timestamp()
            except KeyboardInterrupt:
                break

    def watch_files(self):
        """Keep a watch on files present in sync directories."""
        try:
            wm = WatchManager()
            mask = EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CREATE'] | \
                   EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_DELETE'] | \
                   EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_MODIFY']
            notifier = Notifier(wm, PTmp(self.mfiles, self.rfiles, self.pulled_files))

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
