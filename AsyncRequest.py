# -*- coding: utf-8 -*-
import KBEngine
import time
import threading
import socket
import select
import urllib
from KBEDebug import *
from io import StringIO
from http.client import HTTPResponse


TIME_TYPE_STEP = 0
TIME_TYPE_TIME_OUT = 1

SEND_CNT = '%s %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36\r\n%s'

g_async = None


def _getAsync():
    global g_async
    if g_async == None:
        g_async = KBEngine.createBaseLocally('AsyncRequest', {})
    return g_async


def Request(url, func):
    async = _getAsync()
    async.request(url, None, func)


def Post(url, opt, func):
    async = _getAsync()
    async.request(url, opt, func)


class AsyncRequest(KBEngine.Base):

    def __init__(self):
        KBEngine.Base.__init__(self)

        self._reqs = []
        self._sock = None
        self._write_dt = None
        self._sock_send = False
        self._reqs_curt = None

        self.addTimer(1, 1, TIME_TYPE_STEP)

    def onTimer(self, id, userArg):
        if TIME_TYPE_STEP == userArg:
            self.steps()
        elif TIME_TYPE_TIME_OUT == userArg:
            self.delTimer(id)
            if self._sock:
                KBEngine.deregisterWriteFileDescriptor(self._sock.fileno())
                self._sock.close()
                self._sock = None
            if self._reqs_curt and self._reqs_curt[2]:
                self._reqs_curt[2](None)
            self._reqs_curt = None

    def steps(self):
        if not self._sock and len(self._reqs) > 0:
            try:
                self._reqs_curt = self._reqs.pop()
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock_send = False
                proto, rest = urllib.parse.splittype(self._reqs_curt[0])
                host, rest = urllib.parse.splithost(rest)
                host, port = urllib.parse.splitport(host)
                self._reqs_curt.append(rest)
                self._reqs_curt.append(host)
                self._sock.setblocking(0)
                self._sock.connect_ex((host, int(port) if port else 80))
                self._write_dt = self.addTimer(10, 60, TIME_TYPE_TIME_OUT)
                KBEngine.registerWriteFileDescriptor(self._sock.fileno(), self.onSend)
            except:
                self._reqs.append(self._reqs_curt)
                self.logsError()
                self.cleanSocketStatus()

    def logsError(self):
        import traceback
        ERROR_MSG(traceback.format_exc())

    def logs(self, msg=None):
        INFO_MSG('logs:%s' % (msg))

    def request(self, url, opt={}, func=None):
        self._reqs.append([url, opt, func])

    def onSend(self, fileno):
        if self._sock.fileno() == fileno:
            try:
                KBEngine.deregisterWriteFileDescriptor(self._sock.fileno())
                opt, rest, host, method, end = self._reqs_curt[1], self._reqs_curt[3], self._reqs_curt[4], "GET", "Accept: */*\r\n\r\n"
                if opt and len(opt) > 0:
                    method = 'POST'
                    end = 'Content-Type: application/x-www-form-urlencoded\r\nContent-Length: %s\r\n%s' % self.onHandlePost(opt)
                data = SEND_CNT % (method, rest, host, end)
                self._sock.send(data.encode('utf-8'))
                KBEngine.registerReadFileDescriptor(self._sock.fileno(), self.onRecv)
            except:
                self._reqs.append(self._reqs_curt)
                self.logsError()
                self.cleanSocketStatus()

    def onHandlePost(self, opt):
        ret = ''
        for k in opt:
            ret += '&%s=%s' % (k, opt[k])
        return (len(ret[1:]), '\r\n' + ret[1:] + '\r\n\r\n')

    def onRecv(self, fileno):
        if self._sock.fileno() == fileno:
            self.delTimer(self._write_dt)
            try:
                INFO_MSG('---------------------------onRecv:%s' % self._reqs_curt[0])
                resp = HTTPResponse(self._sock)
                if self._reqs_curt and self._reqs_curt[2]:
                    resp.begin()
                    self._reqs_curt[2](resp)
            except:
                # 出错重新加载
                self._reqs.append(self._reqs_curt)
                self.logsError()
            finally:
                KBEngine.deregisterReadFileDescriptor(self._sock.fileno())
                self.cleanSocketStatus()

    def cleanSocketStatus(self):
        if self._sock:
            self._sock.close()
            self._sock = None
