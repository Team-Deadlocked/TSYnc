import argparse
import logging
import configparser
import os
import sqlite3
import subprocess
from Parent import Base

from Server import Server, ClientData
from client import Client

logger = logging.getLogger('syncIt')

CLIENT_PORT = 8082  # Fixed port for clients
SERVER_PORT = 8081  # Fixed port for servers


def setup_logging(log_filename):
    handler = logging.FileHandler(log_filename)
    #    handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    print('Logging started on file %s' % log_filename)


def get_watch_dirs(user_name, conn):
    watch_dirs = []
    c = conn.cursor()
    c.execute("SELECT * FROM Directories")
    rows = c.fetchall()
    for row in rows:
        dir = os.path.expanduser(row[0])
        my_dir = Base.get_path(dir, user_name)
        watch_dirs.append(my_dir)
    conn.commit()
    # for key, value in config.items('syncit.dirs'):
    #    dir = os.path.expanduser(value.strip())
    #    my_dir = Node.get_dest_path(dir, user_name)
    #    watch_dirs.append(my_dir)
    logger.debug("watched dirs %s", watch_dirs)
    return watch_dirs


def get_clients(conn):
    clients = []
    c = conn.cursor()
    c.execute("SELECT * FROM Clients")
    rows = c.fetchall()
    for row in rows:
        client_uname, client_ip, client_port = row
        clients.append(ClientData(client_uname, client_ip, int(client_port)))
    conn.commit()
    # for key, value in config.items('syncit.clients'):
    #    words = value.split(',')
    #    client_uname, client_ip, client_port = [word.strip() for word in words]
    #    clients.append(ClientData(client_uname, client_ip, int(client_port)))
    return clients


def get_server_tuple(conn):
    c = conn.cursor()
    c.execute("SELECT * FROM Servers")
    row = c.fetchone()
    server_uname, server_ip, server_port = row
    conn.commit()
    return server_uname, server_ip, server_port


def main():
    # use argparse to get role, ip, port and user name
    parser = argparse.ArgumentParser(
        description="""PySyncIt""",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        '-role', help='Specify the role of this machine - client or server', required=True)

    args = parser.parse_args()

    # Retrieving IP address using 'hostname -I' command
    ip_address = subprocess.check_output(['hostname', '-I']).decode().strip()

    # Retrieving username using 'whoami' command
    user_name = subprocess.check_output(['whoami']).decode().strip()

    # start logging
    setup_logging("syncit.log.%s-%s" % (ip_address, CLIENT_PORT if args.role == 'client' else SERVER_PORT))
    logger = logging.getLogger('syncIt')

    # connect database
    conn = sqlite3.connect('database.db')

    if (args.role == 'server'):
        node = Server(args.role, ip_address, SERVER_PORT, user_name, get_watch_dirs(user_name, conn), get_clients(conn))
    else:
        server_uname, server_ip, server_port = get_server_tuple(conn)
        try:
            server_port = int(server_port)
        except ValueError:
            logger.error("Server port must be an integer.")
            return
        node = Client(args.role, ip_address, CLIENT_PORT, user_name, get_watch_dirs(user_name, conn),
                      (server_uname, server_ip, server_port))

    node.activate()
    conn.close()


if __name__ == "__main__":
    main()
