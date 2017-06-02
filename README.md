# KBEngine-MinHTTPServer
KBEngine MinHTTPServer


```python

def index(req, resp):
    resp.body = ('Hello %s' % (req.params.get('name', 'Tom'))).encode()
    resp.end()


server = MinHTTPServer.MinHTTPServer()
server.listen(8090)
server.staticRes('html')
server.route('/index.html', index)


# GET
AsyncRequest.Request('http://www.baidu.com',lambda x:print(x.read()))
# POST
AsyncRequest.Post('http://www.baidu.com',{'key':11},lambda x:print(x.read()))

```