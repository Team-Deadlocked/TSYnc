#BASE CLASS FOR BOTH SERVER AND CLIENT
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import os
import threading
import logging
import re
import subprocess
import traceback

logger = logging.getLogger("TSYnc")
logger.setLevel(logging.DEBUG)


class functionHandler(SimpleXMLRPCRequestHandler):  #needed class to return a requested function call from server side
    def _dispatch(self, method, params):
        try:
            return self.server.funcs[method](*params)
        except:
            traceback.print_exc()
            raise


class Base(object):
    def __init__(self, role , ip, port, uname, watch_dirs):
        self.role = role
        self.ip = ip
        self.port = port
        self.username = uname
        self.watch_dirs = watch_dirs

    @staticmethod
    def get_dest_path(filename, dest_uname):
        user_dir_pattern = re.compile("/home/[^ ]*?/")

        if re.search(user_dir_pattern, filename):
            destpath = user_dir_pattern.sub("/home/%s/" % dest_uname, filename)
        logger.debug("destpath %s", destpath)
        return destpath

    @staticmethod
    def push_file(filename, dest_uname, dest_ip):
        proc = subprocess.Popen(['scp', filename, "%s@%s:%s" % (dest_uname, dest_ip, Node.get_dest_path(filename, dest_uname))])
        return_status = proc.wait()
        logger.debug("returned status %s",return_status)

    def dir_maker(self):  #in the event that the directory isn't present,make it first
        for dir in self.watch_dirs:
            if not os.path.isdir(dir):
                os.makedirs(dir)

    def begin(self):
        server = SimpleXMLRPCServer(("0.0.0.0", self.port), allow_none=True)
        server.register_instance(self)
        server.register_introspection_functions()
        thread = threading.Thread(
            target=server.serve_forever)  #run the program asynchoronously so that the threads run separately
        thread.start()
        logger.debug("Started server thread. Listening on %s", self.port)

    def begin_sync_thread(self):
        sync_thread = threading.Thread(
            target=self.sync_files)  #call the respective sync_files method of the server/client
        sync_thread.start()
        logger.info("Sync begins")

    def activate(self):
        self.dir_maker()
        self.begin_sync_thread()
        self.begin()
