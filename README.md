# KBEngine-MinHTTPServer
KBEngine MinHTTPServer


```python

def index(req, resp):
    resp.body = ('Hello %s' % (req.params.get('name', 'Tom'))).encode()
    resp.end()



server = MinHTTPServer.MinHTTPServer()
server.listen(8090)
server.route('/', index)



```