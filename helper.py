from twisted.web.resource import Resource
from twisted.web.static import Data
from twisted.web.server import Site
from twisted.internet import reactor
import threading

class StatusWrapper(Resource):
    isLeaf = True
    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server

    def render_GET(self, request):
        return "<html><body><PRE>%s</PRE></body></html>"%(self.work_server.queue)

class DataLeaf(Data):
    isLeaf = True

class WorkWrapper(Resource):
    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server
        self.status = StatusWrapper(work_server)

    def getChild(self, name, request):
        print "getchild", name, request
        if name == '':
            return self.status
        if name == 'work':
            return DataLeaf(str(self.work_server.next_job()), 'text/plain')
        if name == 'data':
            print "datareq", request, request.postpath
            val = self.work_server.data_callback(request)
            print val
            return DataLeaf(*val)
        return self

    def render_GET(self, request):
        return "default workwrapper", request

class Helper(object):
    def __init__(self, work_server):
        self.site = Site(WorkWrapper(work_server))

    def start(self, port):
        reactor.listenTCP(port, self.site)
        threading.Thread(None, reactor.run, "Twisted reactor thread", kwargs={'installSignalHandlers' : 0}).start()

    def stop(self):
        reactor.callFromThread(reactor.stop)

