from twisted.web.resource import Resource
from twisted.web.static import Data, File
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.client import getPage
import threading
import urllib, urllib2

class StatusWrapper(Resource):
    isLeaf = True
    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server

    def render_GET(self, request):
        return "<html><body><PRE>%s</PRE></body></html>"%(self.work_server.queue)

class DataLeaf(Data):
    isLeaf = True

class FileLeaf(File):
    isLeaf = True

class Receiver(Resource):
    isLeaf = True
    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server

    def render_POST(self, request):
        result = request.args.copy()
        jobnum = int(result['jobnum'].pop())
        if len(result['jobnum']) == 0:
            del result['jobnum']
        self.work_server.receive_work(jobnum, result)
        return '<html><body>thanks</body></html>'


class WorkWrapper(Resource):
    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server
        self.status = StatusWrapper(work_server)

    def getChild(self, name, request):
        print "getchild", name, request
        if request.method == 'POST':
            return Receiver(self.work_server)
        if name == '':
            return self.status
        if name == 'work':
            workstr = self.work_server.next_job()
            assert isinstance(workstr, str) or isinstance(workstr, unicode)
            return DataLeaf(workstr, 'text/plain')
        if name == 'data':
            val = self.work_server.data_callback(request.postpath)
            if isinstance(val, tuple):
                return DataLeaf(*val)
            else:
                return FileLeaf(val, 'application/octet-stream')
        return self

    def render_GET(self, request):
        return "default workwrapper", request


__started = False
def start_reactor():
    global __started
    if not __started:
        threading.Thread(None, reactor.run, "Twisted reactor thread", kwargs={'installSignalHandlers' : 0}).start()
        __started = True

class Helper(object):
    def __init__(self, work_server, port):
        self.site = Site(WorkWrapper(work_server)) 
        self.port = port
        self.lock = threading.Lock()
        self.listening = False

    def start(self, port):
        start_reactor()
        with self.lock:
            if not self.listening:
                reactor.callFromThread(self.start_listening)

    def stop(self):
        with self.lock:
            if self.listening:
                reactor.callFromThread(self.stop_listening)

    def start_listening(self):
        with self.lock:
            self.port = reactor.listenTCP(self.port, self.site)
            self.listening = True

    def stop_listening(self):
        with self.lock:
            self.port.stopListening()
            self.listening = False

def report_result(base_url, jobnum, **kwargs):
    # we have to be encode the POST data like this, to ensure the
    # nuageux jobnum is first (in case the user uses their own
    # "jobnum" value.
    postdata = urllib.urlencode(zip(['jobnum'] + kwargs.keys(),
                                    [jobnum] + kwargs.values()))
    print "REPORT", urllib2.urlopen(base_url, postdata).read()
