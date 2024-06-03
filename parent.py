from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import os
import threading
import logging
import re
import subprocess
import traceback

logger = logging.getLogger("syncIt")
logger.setLevel(logging.DEBUG)

class FunctionHandler(SimpleXMLRPCRequestHandler):
    """Custom request handler to return a requested function call from the server side."""
    def _dispatch(self, method, params):
        try:
            logger.debug("Server type: %s", type(self.server))
            logger.debug("Server funcs: %s", self.server.funcs)
            return self.server.funcs[method](*params)
        except:
            traceback.print_exc()
            raise

class Base:
    """Base class for both Server and Client."""
    def __init__(self, role, ip, port, uname, watch_dirs):
        self.role = role
        self.ip = ip
        self.port = port
        self.username = uname
        self.watch_dirs = watch_dirs

        # Register the methods for XML-RPC
        self.server = SimpleXMLRPCServer((self.ip, self.port), requestHandler=FunctionHandler, allow_none=True)
        self.server.funcs = {}
        self.register_methods()
        self.server.register_introspection_functions()

    def register_methods(self):
        """Register XML-RPC methods."""
        self.server.funcs['req_push_file'] = self.req_push_file
        self.server.funcs['ack_push_file'] = self.ack_push_file
        self.server.funcs['get_public_key'] = self.get_public_key
        #self.server.funcs['pull_file'] = self.pull_file

    def ack_push_file(self, *args):
        """Acknowledge the successful push of a file."""
        logger.debug("Acknowledge push file request: %s", args)
        return True

    def req_push_file(self, filename, dest_uname, dest_ip):
        """Handle the req_push_file XML-RPC request."""
        logger.debug("Received request to push file: %s to %s@%s", filename, dest_uname, dest_ip)

        # Modify the destination path to include .tsync
        dest_path = os.path.join("/home", dest_uname, ".tsync", filename.lstrip('/'))

        self.push_file(filename, dest_path, dest_ip)
        return True

    @staticmethod
    def get_dest_path(filename, dest_uname, role):
        """Get the destination path for a file, replacing the username in the path."""
        user_dir_pattern = re.compile("/home/[^ ]*?/")
        destpath = None
        if re.search(user_dir_pattern, filename):
            if role == 'server':
                destpath = user_dir_pattern.sub(f"/home/{dest_uname}/.tsync/", filename)
            else:  # role == 'client'
                destpath = user_dir_pattern.sub(f"/home/{dest_uname}/", filename)
        logger.debug("Destination path: %s", destpath)
        return destpath


    @staticmethod
    def push_file(filename, dest_uname, dest_ip, role):
        """Push a file to the destination user and IP using scp."""
        try:
            dest_path = Base.get_dest_path(filename, dest_uname, role)
            proc = subprocess.Popen(['scp', filename, f"{dest_uname}@{dest_ip}:{dest_path}"])
            return_status = proc.wait()
            logger.debug("SCP returned status in push_file of base class: %s", return_status)
        except Exception as e:
            logger.error("Error pushing file: %s", e)

    def get_public_key(self, *args):
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

    # def pull_file(self, filename, source_uname, source_ip , role):
    #     """Pull file 'filename' from the source."""
    #     my_file = Base.get_dest_path(filename, self.username, self.role)
    #     proc = subprocess.Popen(['scp', f"{source_uname}@{source_ip}:{filename}", my_file])
    #     return_status = proc.wait()
    #     logger.debug("SCP returned status: %s", return_status)

    def dir_maker(self):
        """Create directories if they do not exist."""
        base_dir = f"/home/{self.username}/.tsync"
        if not os.path.isdir(base_dir):
            try:
                os.makedirs(base_dir)
                logger.info("Created directory: %s", base_dir)
            except Exception as e:
                logger.error("Error creating directory %s: %s", base_dir, e)

        for dir in self.watch_dirs:
            # Create the original directory if it doesn't exist
            if not os.path.isdir(dir):
                try:
                    os.makedirs(dir)
                    logger.info("Created directory: %s", dir)
                except Exception as e:
                    logger.error("Error creating directory %s: %s", dir, e)

            # Create a corresponding directory inside .tsync
            relative_dir = os.path.relpath(dir, start='/home/' + self.username)
            tsync_dir = os.path.join(base_dir, relative_dir)
            if not os.path.isdir(tsync_dir):
                try:
                    os.makedirs(tsync_dir)
                    logger.info("Created directory: %s", tsync_dir)
                except Exception as e:
                    logger.error("Error creating directory %s: %s", tsync_dir, e)

    def begin(self):
        """Start the XML-RPC server."""
        thread = threading.Thread(target=self.server.serve_forever)  # Run the server asynchronously
        thread.start()
        logger.debug("Started server thread. Listening on port %s", self.port)

    def begin_sync_thread(self):
        """Start the synchronization thread."""
        sync_thread = threading.Thread(target=self.sync_files)  # Call the respective sync_files method of the server/client
        sync_thread.start()
        logger.info("Sync thread started")

    def activate(self):
        """Activate the base functionalities including directory creation and starting threads."""
        self.dir_maker()
        self.begin_sync_thread()
        self.begin()
