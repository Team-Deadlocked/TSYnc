# client_test.py
import xmlrpc.client

proxy = xmlrpc.client.ServerProxy("http://10.0.2.15:8082")
print(proxy.test_function())
