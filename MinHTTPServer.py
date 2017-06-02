# -*- coding: utf-8 -*-
import KBEngine
import Functor
import socket
import urllib.parse
from io import StringIO
from KBEDebug import *


_MAXLINE = 65536
_DEFAULT_ERROR_CONTENT_TYPE = "text/html;charset=utf-8"


class HTTPResponse:

    def __init__(self, sock):
        self._sock = sock
        self.version = 'HTTP/1.1'
        self.status = 200
        self.body = b''
        self._headers = []
        self._complete = False

    def complete(self):
        return self._complete

    def send_error(self, code):
        self.status = code
        self.send_header("Content-Type", _DEFAULT_ERROR_CONTENT_TYPE)
        self.end()

    def send_header(self, keyword, value):
        self._headers.append("%s: %s\r\n" % (keyword, value))

    def end(self):
        if not self._complete:
            self._complete = True
            self.send_header('Connection', 'close')
            self.send_header('Content-Length', int(len(self.body)))
            cnt = '%s %d ok\r\n%s\r\n' % (self.version, self.status, ''.join(self._headers))
            self._sock.send(cnt.encode('latin-1', 'strict'))
            self._sock.send(self.body)
            self._sock.send(b'\r\n')
            self._sock.close()
        else:
            raise Exception('HTTPResponse is complete')


class HTTPRequest:

    def __init__(self, sock):
        self._rfile = None
        self.method = None
        self.url = None
        self.version = None
        self.headers = {}
        self.params = {}

        self.recv_bytes(sock)
        self.parse_request()

    def recv_bytes(self, sock):
        datas = b''
        while True:
            data = sock.recv(_MAXLINE + 1)
            datas += data
            if len(data) <= _MAXLINE + 1:
                break
        self._rfile = StringIO(str(datas, 'iso-8859-1'))

    def parse_request(self):
        line = self._rfile.readline(_MAXLINE + 1)
        if len(line) > _MAXLINE:
            return self.send_error(414)
        words = line.rstrip('\r\n').split()
        if len(words) != 3:
            return self.send_error(400)
        self.method, self.url, self.version = words
        code, err = self.parse_headers()
        if code:
            return self.send_error(code, err)
        self.parse_params()
        if self.method == 'POST':
            self.parse_data()

    def parse_data(self):
        while True:
            line = self._rfile.readline()
            if line in ('\r\n', '\n', ''):
                break
            for i in line.rstrip('\r\n').split('&'):
                words = i.split('=')
                self.params[words[0]] = words[1]

    def parse_params(self):
        pos = self.url.find('?')
        if pos != -1:
            for i in self.url[pos + 1:].split('&'):
                words = i.split('=')
                self.params[words[0]] = words[1]

    def parse_headers(self):
        while True:
            line = self._rfile.readline(_MAXLINE + 1)
            if len(line) > _MAXLINE:
                return (414, '')
            if line in ('\r\n', '\n', ''):
                break
            words = line.rstrip('\r\n').split(':')
            self.headers[words[0]] = ':'.join(words[1:])
        return (None, None)

    def param(self, key, value=None):
        return self.params.get(key, value)

    def parseParam(self, key, value=None):
        return urllib.parse.unquote(self.params.get(key, value)) if key in self.params.keys() else value


class MinHTTPServer:

    def __init__(self):
        self._sock = None
        self._resPath = None
        self._handler = {}

    def listen(self, port, addr='0.0.0.0'):
        if not self._sock and port > 0:
            self._sock = socket.socket()
            self._sock.bind((addr, port))
            self._sock.listen(10)
            KBEngine.registerReadFileDescriptor(self._sock.fileno(), self.onAccept)
            return True
        return False

    def staticRes(self, resPath=None):
        self._resPath = resPath

    def route(self, url, func):
        if url and func:
            if url not in self._handler:
                self._handler[url] = []
            self._handler[url].append(func)

    def onAccept(self, fileno):
        if self._sock.fileno() == fileno:
            sock, addr = self._sock.accept()
            KBEngine.registerReadFileDescriptor(sock.fileno(), Functor.Functor(self.onRecv, sock, addr))

    def onRecv(self, sock, addr, fileno):
        KBEngine.deregisterReadFileDescriptor(sock.fileno())
        try:
            req, resp = HTTPRequest(sock), HTTPResponse(sock)
            for k, v in self._handler.items():
                if req.url.startswith(k):
                    for func in v:
                        try:
                            func(req, resp)
                        except:
                            pass
                        finally:
                            if resp.complete():
                                return
            if self._resPath:
                self.onRespStaticRes(req, resp)

        except:
            sock.close()

    def onRespStaticRes(self, req, resp):
        filePath = '%s%s' % (self._resPath, req.url if req.url[-1] != '/' else ('%sindex.html' % req.url))
        if KBEngine.hasRes(filePath):
            file = KBEngine.open(filePath, 'rb')
            resp.body = file.read()
            file.close()
        else:
            resp.body = b'File Not Found...'
        resp.end()
