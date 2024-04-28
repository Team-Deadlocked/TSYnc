import socket
import errno
import logging
import xmlrpc.client

logger = logging.getLogger('Tsync')
logger.setLevel(logging.DEBUG)
def make_safer(fn):
    def wrapped(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
            if result is None:
                result = "Success"
            return result
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED or e.errno == errno.EHOSTUNREACH:
                logger.critical("Connection error while calling RPC function '%s': %s", fn.__name__, str(e))
                logger.critical("Failed to connect to RPC server at %s:%s", args[0], args[1])
                return None
            else:
                raise
    return wrapped

@make_safer
def pull_file(dest_ip, dest_port, filename, source_uname, source_ip):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (source_ip, dest_port),allow_none=True)
    connect.pull_file(filename, source_uname, source_ip)

@make_safer
def req_push_file(dest_ip, dest_port, filename, source_uname, source_ip):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (dest_ip, dest_port),allow_none=True)
    return connect.req_push_file(filename, source_uname, source_ip)

@make_safer
def ack_push_file(dest_ip, dest_port, filename, source_uname, source_ip):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (dest_ip, dest_port),allow_none=True)
    return connect.ack_push_file(filename, source_uname, source_ip)

@make_safer
def mark_presence(dest_ip, dest_port, source_ip, source_port):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (dest_ip, dest_port),allow_none=True)
    logger.debug("RPC call to mark available")
    logger.debug("Available methods on RPC server: %s", connect.system.listMethods())
    connect.mark_presence(source_ip, source_port)

@make_safer
def get_client_public_key(dest_ip, dest_port):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (dest_ip, dest_port),allow_none=True)
    return connect.get_public_key()

@make_safer
def find_available(dest_ip, dest_port):
    connect = xmlrpc.client.ServerProxy("http://%s:%d" % (dest_ip, dest_port),allow_none=True)
    try:
        connect.system.listMethods()
        return True
    except socket.error as e:
        if e.errno == errno.ECONNREFUSED or e.errno == errno.EHOSTUNREACH:
            return False
        else:
            raise




