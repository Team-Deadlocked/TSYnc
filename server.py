import logging
import shutil
import re
import threading
import time
import errno
from parent import Base
import subprocess
import os
import sxmlr
from persistence import FileData, FilesPersistentSet, PersistentSet

logger = logging.getLogger('tsync')
logger.setLevel(logging.DEBUG)

def is_collision_file(filename):
    """Check if the given filename is a collision backup file."""
    backup_file_pattern = re.compile(r"\.backup\.[1-9]+\.")
    return re.search(backup_file_pattern, filename) is not None

class ClientData:
    """Data corresponding to each client residing in server object."""

    def __init__(self, client_uname, client_ip, client_port):
        self.available = False
        self.mfiles = PersistentSet(f'server-{client_uname}.pkl')
        self.uname = client_uname
        self.ip = client_ip
        self.port = client_port

class Server(Base):
    """Server class to manage file synchronization and client availability."""

    def __init__(self, role, ip, port, uname, watch_dirs, clients):
        super(Server, self).__init__(role, ip, port, uname, watch_dirs)
        self.funcs = {
            'ack_push_file': self.ack_push_file,
            'mark_presence': self.mark_presence,
            'req_push_file': self.req_push_file,
            'sync_files': self.sync_files,
            'add_client_keys': self.add_client_keys,
            'collision_check': self.collision_check,
            'find_available_clients': self.find_available_clients,
            'get_authfile': self.get_authfile,
            'get_client_public_key': sxmlr.get_client_public_key,
            'find_available': sxmlr.find_available,
            'get_public_key': self.get_public_key,

        }
        self.clients = clients

    def req_push_file(self, filedata, source_uname, source_ip, source_port):
        """Handle file push request from a client."""
        logger.debug("server filedata %s %s", filedata['name'], list(filedata.keys()))

        # Add self.role as an argument to the get_dest_path method
        my_file = Base.get_dest_path(filedata['name'], self.username, self.role)

        if self.collision_check(filedata):
            server_filename = f"{my_file}.backup.{filedata['time']}.{source_uname}.{source_ip}:{source_port}"
        else:
            server_filename = my_file

        logger.debug("server filename %s returned for file %s", server_filename, filedata['name'])
        return server_filename

    def ack_push_file(self, server_filename, source_uname, source_ip, source_port):
        """Acknowledge the successful push of a file."""
        # if is_collision_file(server_filename):
        #     return

        for client in self.clients:
            if (client.ip, client.port) == (source_ip, source_port):
                continue
            client.mfiles.add(server_filename)  # the file is in the server's directory ./.tsync
            logger.debug("File added to modified list for client %s", client.uname)

    def collision_check(self, filedata):
        """Check for file collision based on modification time."""
        # Add self.role as an argument to the get_dest_path method
        my_file = Base.get_dest_path(filedata['name'], self.username, self.role)
        try:
            collision_exist = os.path.getmtime(my_file) > filedata['time']
            logger.debug("Collision check: server time %s  client time %s", os.path.getmtime(my_file), filedata['time'])
        except OSError as e:
            if e.errno == errno.ENOENT:
                collision_exist = False
            else:
                raise
        logger.debug("Collision check for file %s result %s", my_file, collision_exist)
        return collision_exist

    def sync_files(self):
        """Synchronize files with all available clients."""
        while True:
            try:
                time.sleep(10)
                for client in self.clients:
                    logger.debug("List of files for client %s, availability %s", client.uname, client.available)
                    if client.available:
                        for file in client.mfiles.list():
                            rpc_status = sxmlr.pull_file(client.ip, client.port, file, self.username, self.ip)
                            if rpc_status is None:
                                client.available = False
                                continue
                            client.mfiles.remove(file)
                            logger.debug("File synced: %s", file)
            except KeyboardInterrupt:
                break

    def mark_presence(self, client_ip, client_port):
        """Mark client as available."""
        logger.debug("Mark presence call received from %s:%s", client_ip, client_port)
        for client in self.clients:
            if (client_ip, client_port) == (client.ip, client.port):
                client.available = True
                logger.debug("Client %s marked available", client.uname)
                self.add_client_keys(client)

    def find_available_clients(self):
        """Check availability of all clients."""
        for client in self.clients:
            client.available = sxmlr.find_available(client.ip, client.port)
            self.add_client_keys(client)

    def get_authfile(self):
        """Get the path to the authorized_keys file."""
        return os.path.join("/home", self.username, ".ssh/authorized_keys")

    def add_client_keys(self, client):
        """Add the public key of a client to the authorized_keys file."""
        authfile = self.get_authfile()
        client_pub_key = sxmlr.get_client_public_key(client.ip, client.port)

        if client_pub_key is None:
            return

        with open(authfile, 'a+') as fp:
            if client_pub_key not in fp.readlines():
                fp.write(client_pub_key + '\n')
                logger.debug("Added public key for client %s", client.uname)

    def get_public_key(self):
        """Method to get the public key."""
        try:
            with open(os.path.join("/home", self.username, ".ssh/id_rsa.pub"), 'r') as key_file:
                public_key = key_file.read().strip()
            return public_key
        except FileNotFoundError:
            logger.error("Public key file not found.")
            return None
        except Exception as e:
            logger.error("Error reading public key file: %s", e)
            return None
    def activate(self):
        """Activate the server node."""
        super(Server, self).activate()
        self.find_available_clients()
