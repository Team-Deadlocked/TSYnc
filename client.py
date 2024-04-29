import logging
import os

import pyinotify
from pyinotify import WatchManager
from pyinotify import ProcessEvent

import sxmlr
from Parent import Base
import subprocess
import time
import threading


logger = logging.getLogger('TSync')
logger.setLevel(logging.DEBUG)

class Watchdog(ProcessEvent):
    def my_init(self, mfiles,rfiles,pulled_files):
        self.mfiles = mfiles
        self.rfiles = rfiles
        self.pulled_files = pulled_files

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
    def __init__(self, role,ip,port,uname,dirs,server):
        super(Client,self).__init__(role,ip,port,uname,dirs)
        self.server=server
        self.mfiles=FilesPersistentSet(pkl_filename='client.pkl')   # ** to change **
        self.rfiles=set()
        self.pulled_files=set()
        self.server_available=True


    def push_file(self, filename, dest_file, dest_uname, dest_ip):
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, dest_file)])
        return_status = proc.wait()
        logger.debug("push_file from client.py -> Return status %s",return_status)
        return return_status

    def pull_file(self,filename,source_uname,source_ip):
        my_file=Base.get_path(filename,self.username)
        self.pulled_files.add(my_file)
        proc=subprocess.Popen(['scp',"%s@%s:%s"%(source_uname,source_ip,my_file),my_file])
        return_status=proc.wait()
        logger.debug("pull_file from client.py -> Return status %s",return_status)
        return return_status

    def get_public_key(self):
        pubkey = None
        pubkey_dirname = os.path.join(os.path.expanduser('~'), '.ssh')
        logger.debug("get_public_key from client.py -> pubkey_dirname %s", pubkey_dirname)
        for tuple in os.walk(pubkey_dirname):
            dirname, dirnames, filenames = tuple
            break
        logger.debug("get_public_key from client.py -> public key dir files %s", filenames)
        for filename in filenames:
            if filename.endswith('.pub'):
                pubkey_filepath = os.path.join(dirname, filename)
                logger.debug("get_public_key from client.py -> pubkey_filepath %s", pubkey_filepath)
                pubkey = open(pubkey_filepath, 'r').readline()
                logger.debug("get_public_key from client.py -> pubkey %s", pubkey)

        return pubkey

    def find_modified(self):
        for directory in self.watch_dirs:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    mtime = os.path.getmtime(file_path)
                    last_modified = self.mfiles.get_modified_timestamp()  # Get the timestamp
                    if last_modified is not None and mtime > last_modified:
                        logger.debug("find_modified_files from clent.py -> File %s modified", file_path)
                        self.mfiles.add(file_path, mtime)



    def sync_files(self):
        mfiles = self.mfiles
        while True:
            try:
                time.sleep(10)
                for filedata in mfiles.list():
                    filename = filedata.name
                    logger.debug("sync_files from client.py -> push filedata object to server %s", filedata)
                    server_uname , server_ip ,server_port = self.server
                    dest_file = sxmlr.req_push_file(server_ip,server_port,filedata,self.username,self.ip,self.port)
                    logger.debug("sync_files from client.py -> destination file name %s", dest_file)
                    if dest_file is None:
                        break
                    push_status = self.push_file(filename,dest_file,server_uname,server_ip)
                    if push_status < 0:
                        break
                    xrpc_status = sxmlr.ack_push_file(server_ip, server_port, dest_file, self.username, self.ip,
                                                    self.port)
                    if xrpc_status is None:
                        break
                    mfiles.remove(filename)
                self.mfiles.update_modified_timestamp()
            except KeyboardInterrupt:
                break

    def watch_files(self):
        wm = WatchManager()
        mask = pyinotify.IN_CREATE | pyinotify.IN_DELETE | pyinotify.IN_MODIFY
        notifier = pyinotify.Notifier(wm, Watchdog(self.mfiles, self.rfiles, self.pulled_files))
        logger.debug("watch_files from client.py -> watch_dirs %s", self.watch_dirs)
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

    def start_watch_thread(self):
        watch_thread = threading.Thread(target=self.watch_files)
        watch_thread.start()
        logger.info("start_watch_thread from client.py -> Thread 'watchfiles' started ")

    def mark_presence(self):
        server_uname, server_ip, server_port = self.server
        logger.debug("mark_presence from client.py -> client call to mark available to the server")
        sxmlr.mark_presence(server_ip, server_port, self.ip, self.port)
        logger.debug("mark_presence from client.py -> client marked available")

    def activate(self):
        super(Client, self).activate()
        self.start_watch_thread()
        self.mark_presence()
        self.find_modified()