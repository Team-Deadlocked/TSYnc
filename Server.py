import logging
import re
import threading
import time
import errno
from Parent import Base
import subprocess
import os
import sxmlr

logger=logging.getLogger("TSYnc")

def is_collision_file(filename):
    backup_pattern = re.compile(r"\.backup\.[1-9]+\.")
    if re.search(backup_pattern, filename) is None:
        return False
    else:
        return True

class Server(Base):
    def __init__(self, role,ip,port,uname,dirs,clients):
        super(Server,self).__init__(role,ip,port,uname,dirs)
        self.clients=clients

    def req_push_file(self, file, source_uname, source_ip, source_port):
        logger.debug("%s %s",file['name'],list(file.keys()))
        path = Base.get_path(file['name'], self.username)

        if self.collision(file):
            #file_name = "%s.backup.%s.%s.%s:%s"%(path,file['time'],source_uname,source_ip,source_port)
            pass
        else:
            file_name = path

        logger.debug("Path is given as %s",file_name)
        return file_name

    def file_notify(self,filename, source_uname, source_ip, source_port):
        if is_collision_file(filename):
            return
        for client in self.clients:
            if(client.ip,client.port)==(source_ip,source_port):
                continue #no need to notify the one updating itself
            else:
                client.mfiles.add(filename)
                logger.debug("Client modified")

    def collision_check(self, filedata):
        file=Base.get_path(filedata['name'],self.username)
        try:
            is_collision = os.path.getmtime(file)>filedata['time']
        except OSError as e:
            if e.errno == errno.ENOENT:
                is_collison= False
            else:
                raise
        logger.debug("Result of collision: %s",is_collision)
        return is_collision

    def sync_files(self):
        while True:
            try:
                time.sleep(10)
                for client in self.clients:
                    if client.available:
                        for file in client.mfiles.list():
                            rpc_status = sxmlr.pull_file(client.ip,client.port,file,self.username,self.ip)

                            if rpc_status is None:
                                client.available=False
                                continue
                            client.mfiles.remove(file)
            except KeyboardInterrupt:
                break

    def mark_presence(self, client_ip, client_port):
        """Mark client as available"""
        logger.debug("mark available call received")
        for client in self.clients:
            if (client_ip, client_port) == (client.ip, client.port):
                client.available = True
                logger.debug("client with ip %s, marked available", client_ip)
                self.add_client_keys(client)

    def find_available_clients(self):
        for client in self.clients:
            client.available = sxmlr.find_available(client.ip,client.port)
            self.add_client_keys(client)

    def get_authfile(self):
        return os.path.join("/home", self.username, ".ssh/authorized_keys")

    def add_client_keys(self, client):
        """ Add public keys corresponding to user """
        authfile = self.get_authfile()
        client_pub_key = sxmlr.get_client_public_key(client.ip, client.port)

        if client_pub_key is None:
            return

        with open(authfile, 'a+') as fp:
            if client_pub_key not in fp.readlines():
                fp.write(client_pub_key + '\n')

    def activate(self):
        """ Activate Server Node """
        super(Server, self).activate()
        self.find_available_clients()