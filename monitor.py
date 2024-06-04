import argparse
import logging
import configparser
import os
from parent import Base
from server import Server, ClientData
from client import Client

logger = logging.getLogger('tsync')


def setup_logging(log_filename):
    """Setup logging configuration."""
    handler = logging.FileHandler(log_filename)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info('Logging started on file %s', log_filename)


def get_watch_dirs(config, user_name, role):
    """Retrieve and return directories to watch from configuration."""
    watch_dirs = []
    for key, value in config.items('tsync.dirs'):
        dir = os.path.expanduser(value.strip())
        my_dir = Base.get_dest_path(dir, user_name, role)
        watch_dirs.append(my_dir)
    logger.debug("Watched dirs: %s", watch_dirs)
    return watch_dirs


def get_clients(config):
    """Retrieve and return client data from configuration."""
    clients = []
    for key, value in config.items('tsync.clients'):
        client_uname, client_ip, client_port = [word.strip() for word in value.split(',')]
        clients.append(ClientData(client_uname, client_ip, int(client_port)))
    logger.debug("Client data: %s", clients)
    return clients


def get_server_tuple(config):
    """Retrieve and return server information from configuration."""
    server_info = config.get('tsync.server', 'server')
    server_uname, server_ip, server_port = [item.strip() for item in server_info.split(',')]
    logger.debug("Server info: %s, %s, %s", server_uname, server_ip, server_port)
    return server_uname, server_ip, server_port


def load_config(config_file='tsync.cfg'):
    """Load configuration from the specified file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    logger.info("Using config file: %s", config_file)
    return config


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="TSYnc", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-ip', help='Specify the IP address of this machine', required=True)
    parser.add_argument('-port', help='Specify the port of this machine to run RPC server', required=True)
    parser.add_argument('-uname', help='Specify the user name of this machine', required=True)
    parser.add_argument('-role', help='Specify the role of this machine - client or server', required=True)

    args = parser.parse_args()

    log_filename = f"tsync.log.{args.ip}-{args.port}"
    setup_logging(log_filename)

    config = load_config()

    if args.role == 'server':
        node = Server(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(config, args.uname, args.role),
                      get_clients(config))
    else:
        node = Client(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(config, args.uname, args.role),
                      get_server_tuple(config))

    node.activate()


if __name__ == "__main__":
    main()
