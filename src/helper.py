from twisted.web.resource import Resource
from twisted.web.static import Data, File
from twisted.web.server import Site
from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.internet.interfaces import IReadDescriptor
from twisted.internet.defer import Deferred
import threading
import urllib, urllib2

try:
    import pybonjour
    has_bonjour = True
except:
    has_bonjour = False

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
        self.advertiser = None

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
            if self.advertiser is not None:
                self.advertiser.stop()
                self.advertiser = None

    def advertise(self, name, protocol):
        with self.lock:
            if self.advertiser is None:
                self.advertiser = Advertiser(name, protocol, self.port)

def report_result(base_url, jobnum, **kwargs):
    # we have to be encode the POST data like this, to ensure the
    # nuageux jobnum is first (in case the user uses their own
    # "jobnum" value.
    postdata = urllib.urlencode(zip(['jobnum'] + kwargs.keys(),
                                    [jobnum] + kwargs.values()))
    print "REPORT", urllib2.urlopen(base_url, postdata).read()

# based on from http://www.indelible.org/ink/twisted-bonjour/
class Advertiser(object):
    def __init__(self, name, protocol, port):
        assert has_bonjour, "Bonjour/Zeroconf required for advertising work."
        self.sdref = None
        d = self.broadcast("_%s._tcp"%(protocol), port, name)
        d.addCallback(self.started_callback)
        d.addErrback(self.failed_callback)

    def started_callback(self, args):
        self.sdref = args[0]
        print "Advertising %s.%s%s"%args[1:]

    def failed_callback(self, errcode):
        print "Advertising failed:", errcode

    def stop(self):
        # race condition if started_callback hasn't been called, when
        # stop() is called.  So don't do that.
        self.sdref.close()

    def broadcast(self, regtype, port, name):
        def _callback(sdref, flags, errorCode, name, regtype, domain):
            if errorCode == pybonjour.kDNSServiceErr_NoError:
                d.callback((sdref, name, regtype, domain))
            else:
                d.errback(errorCode)
        d = Deferred()
        sdref = pybonjour.DNSServiceRegister(name=name,
                                             regtype=regtype,
                                             port=port,
                                             callBack=_callback)
        reactor.addReader(Advertiser.ServiceDescriptor(sdref))
        return d

    class ServiceDescriptor(object):
        def __init__(self, sdref):
            self.sdref = sdref

        def doRead(self):
            pybonjour.DNSServiceProcessResult(self.sdref)

        def fileno(self):
            return self.sdref.fileno()

        def logPrefix(self):
            return "nuageux_bonjour"

        def connectionLost(self, reason):
            self.sdref.close()
