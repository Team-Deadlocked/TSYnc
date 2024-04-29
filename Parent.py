#BASE CLASS FOR BOTH SERVER AND CLIENT
from xmlrpc.server import SimpleXMLRPCServer,SimpleXMLRPCRequestHandler
import os
import threading
import logging
import re
import subprocess
import traceback

logger=logging.getLogger("TSYnc")
logger.setLevel(logging.DEBUG)

class functionHandler(SimpleXMLRPCRequestHandler):#needed class to return a requested function call from server side
    def _dispatch(self, method, params):
        try:
            return self.server.funcs[method](*params)
        except:
            traceback.print_exc()
            raise
class Base(object):
    def __init__(self, role, ip, port, uname, dirs):
        self.role=role #server or client
        self.ip=ip
        self.port=port
        self.username=uname #will be used to retrieve file path
        self.directories=dirs #check for directories

    @staticmethod
    def get_path(filename, dest_uname):
        dir_pattern = re.compile("/home/[^ ]*?/") #set up the pattern of file path

        if re.search(dir_pattern, filename):#look for modified file's file path matcing pattern
            dest_path = dir_pattern.sub("/home/%s",dest_uname)#replace the server's username by client's
        logger.debug("Destination: %s",dest_path)
        return dest_path

    @staticmethod
    def update_file(filename, dest_uname, dest_ip):#Currently using SCP to test
        process = subprocess.Popen(['scp',filename, "%s@%s:%s" % (dest_uname,dest_ip,Base.get_path(filename, dest_uname))])#SCP use method
        status = process.wait()
        logger.debug("Status: %s",status)

    def dir_maker(self):#in the event that the directory isn't present,make it first
        for dir in self.directories:
            if not os.path.isdir(dir):
                os.makedirs(dir)

    def begin(self):
        server = SimpleXMLRPCServer(("0.0.0.0",self.port), allowed=True)
        server.register_instance(self)
        server.register_introspection_functions()
        thread = threading.Thread(target=server.serve_forever)#run the program asynchoronously so that the threads run separately
        thread.start()
        logger.debug("Started server thread. Listening on %s",self.port)

    def begin_sync_thread(self):
        sync_thread=threading.Thread(target=self.sync_files)#call the respective sync_files method of the server/client
        sync_thread.start()
        logger.info("Sync begins")

    def commence(self):
        self.dir_maker()
        self.begin_sync_thread()
        self.begin()