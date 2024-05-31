import socket
import errno
import logging
import xmlrpc.client

logger = logging.getLogger('syncIt')
logger.setLevel(logging.DEBUG)

def make_safer(fn):
    """Decorator to make XML-RPC function calls safer by handling socket errors."""
    def wrapped(*args):
        try:
            result = fn(*args)
            if result is None:
                result = "Success"
            return result
        except socket.error as e:
            if e.errno in (errno.ECONNREFUSED, errno.EHOSTUNREACH):
                logger.critical("Connection error while calling RPC function '%s': %s", fn.__name__, str(e))
                logger.critical("Failed to connect to RPC server at %s:%s", args[0], args[1])
                return None
            else:
                raise
        except Exception as e:
            logger.error("Unexpected error while calling RPC function '%s': %s", fn.__name__, str(e))
            return None
    return wrapped

@make_safer
def pull_file(dest_ip, dest_port, filename, source_uname, source_ip):
    """Request to pull a file from the source."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    connect.pull_file(filename, source_uname, source_ip)

@make_safer
def req_push_file(dest_ip, dest_port, filename, source_uname, source_ip, source_port):
    """Request to push a file to the destination."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    return connect.req_push_file(filename, source_uname, source_ip, source_port)

@make_safer
def ack_push_file(dest_ip, dest_port, filename, source_uname, source_ip, source_port):
    """Acknowledge the push of a file to the destination."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    return connect.ack_push_file(filename, source_uname, source_ip, source_port)

@make_safer
def mark_presence(dest_ip, dest_port, source_ip, source_port):
    """Mark the presence of a client on the network."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    logger.debug("RPC call to mark presence")
    logger.debug("Available methods on RPC server: %s", connect.system.listMethods())
    connect.mark_presence(source_ip, source_port)

@make_safer
def get_client_public_key(dest_ip, dest_port):
    """Retrieve the public key of a client."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    return connect.get_public_key()

@make_safer
def find_available(dest_ip, dest_port):
    """Check if the RPC server is available."""
    connect = xmlrpc.client.ServerProxy(f"http://{dest_ip}:{dest_port}/", allow_none=True)
    try:
        connect.system.listMethods()
        return True
    except socket.error as e:
        if e.errno in (errno.ECONNREFUSED, errno.EHOSTUNREACH):
            return False
        else:
            raise
