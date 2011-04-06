from __future__ import with_statement
import select
import sys
import pybonjour
from collections import deque
import threading
from twisted.web.resource import Resource
from twisted.web.server import Site
from twisted.internet import reactor

class Server(object):
    def __init__(self, name, port=None, use_bonjour=False):
        self.port = port or 8139
        self.jobnum = 0
        self.queue = deque()
        self.completed = {}
        self.lock = threading.Lock()
        self.use_bonjour = use_bonjour
        self.serving = False
        self.helper = Helper(self)

    def add_work(self, work_blob):
        with self.lock:
            self.queue.append((self.jobnum, work_blob))
            this_job = self.jobnum
            self.jobnum += 1
        return this_job

    def fetch_result(self, jobnum=None):
        with self.lock:
            if jobnum is None:
                if len(self.completed):
                    jobnum = self.completed.keys()[0]
                else:
                    return None
            if jobnum in self.completed:
                return self.completed.pop(jobnum)
            return None

    def next_job(self):
        with self.lock:
            jobnum, work_blob = self.queue[0]
            self.queue.rotate(1)
            return (jobnum, work_blob)

    def receive_work(self, jobnum, result_blob):
        with self.lock:
            # only accept the first answer, though we could do some consistency checks here.
            if jobnum not in self.completed:
                self.completed[jobnum] = result_blob
                # This seems the easiest way to remove from the queue given only the jobnum
                # (I guess we could add a self.jobnum_to_work dict, but would it be cleaner?)
                for idx in range(len(self.queue)):
                    if self.queue[0][0] == jobnum:
                        self.queue.popleft()
                    self.queue.rotate(1)

    def start(self):
        self.helper.start(self.port)

    def stop(self):
        self.helper.stop()

    def clear(self):
        with self.lock:
            self.queue.clear()
            self.completed = {}
            

class WorkWrapper(Resource):
    isLeaf = True

    def __init__(self, work_server):
        Resource.__init__(self)
        self.work_server = work_server

    def render_GET(self, request):
        return "Hello, world! I am located at %r. %s" % (request.prepath, request)

class Helper(object):
    def __init__(self, work_server):
        self.site = Site(WorkWrapper(work_server))

    def start(self, port):
        reactor.listenTCP(port, self.site)
        threading.Thread(None, reactor.run, "Twisted reactor thread", kwargs={'installSignalHandlers' : 0}).start()

    def stop(self):
        reactor.callFromThread(reactor.stop)

if __name__ == '__main__':
    s = Server('test', 8180)
    s.start()
    input()
    print threading.activeCount(), "threads"
    s.stop()
    input()
    print threading.activeCount(), "threads"
    
