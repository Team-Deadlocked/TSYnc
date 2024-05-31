# server_test.py
from xmlrpc.server import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler

class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

def test_function():
    return "Server is running"

server = SimpleXMLRPCServer(("10.0.2.15", 8082), requestHandler=RequestHandler)
server.register_function(test_function, "test_function")
print("Server listening on port 8082...")
server.serve_forever()
