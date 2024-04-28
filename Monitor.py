import argparse
import logging
import configparser
import os
import sqlite3
from node import Node

from server import Server, ClientData
from client import Client

logger = logging.getLogger('syncIt')


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
        my_dir = Node.get_dest_path(dir, user_name)
        watch_dirs.append(my_dir)
    conn.commit()
    # for key, value in config.items('syncit.dirs'):
    #    dir = os.path.expanduser(value.strip())
    #    my_dir = Node.get_dest_path(dir, user_name)
    #    watch_dirs.append(my_dir)
    logger.debug("watched dirs ", watch_dirs)
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
        '-ip', help='Specify the ip address of this machine', required=True)

    parser.add_argument(
        '-port', help='Specify the port of this machine to run rpc server', required=True)

    parser.add_argument(
        '-uname', help='Specify the user name of this machine', required=True)

    parser.add_argument(
        '-role', help='Specify the role of this machine - client or server', required=True)

    args = parser.parse_args()

    # start logging
    setup_logging("syncit.log.%s-%s" % (args.ip, args.port));
    logger = logging.getLogger('syncIt')

    # Read config file
    # config = configparser.ConfigParser()
    # logger.info("Using config file: syncit.cfg")
    # config.read('syncit.cfg')

    # connect database
    conn = sqlite3.connect('database.db')

    if (args.role == 'server'):
        node = Server(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(args.uname, conn),
                      get_clients(conn))
    else:
        node = Client(args.role, args.ip, int(args.port), args.uname, get_watch_dirs(args.uname, conn),
                      get_server_tuple(conn))

    node.activate()
    conn.close()


if __name__ == "__main__":
    main()
