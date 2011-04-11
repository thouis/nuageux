from __future__ import with_statement
import select
import sys
from collections import deque
import threading
from helper import Helper, report_result
import socket
import urllib

class Server(object):
    def __init__(self, name, port=None, use_bonjour=False, data_callback=None, validate_result=None):
        '''note that data_callback must be thread safe'''
        self.port = port or 8139
        self.jobnum = 0
        self.queue = deque()
        self.completed = {}
        self.lock = threading.Lock()
        self.use_bonjour = use_bonjour
        self.data_callback = data_callback
        self.validate_result = validate_result
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
            if len(self.queue) > 0:
                jobnum, work_blob = self.queue[0]
                self.queue.rotate(-1)
                return "%d %s"%(jobnum, work_blob)
            else:
                return "NOWORK"

    def receive_work(self, jobnum, result_dict):
        # XXX - this should probably cache results in files, to prevent overload
        # XXX - need to check work is valid before removing from work queue
        if self.validate_result is not None:
            if not self.validate_result(result_dict):
                sys.stderr.write("NUAGEUX: job %s not accepted\n"%(jobnum))
                return
        with self.lock:
            # only accept the first answer, though we could do some consistency checks here.
            if jobnum not in self.completed:
                self.completed[jobnum] = result_dict
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

    def base_URL(self):
        return 'http://%s:%d'%(socket.getfqdn(), self.port)
            
if __name__ == '__main__':
    def data_callback(str):
        print "ser", str
        return "data '%s'"%(str), 'text/plain'

    s = Server('test', 8180, data_callback=data_callback)
    s.start()
    s.add_work('first job')
    s.add_work('second job')
    input()
    print threading.activeCount(), "threads"
    s.stop()
    input()
    print threading.activeCount(), "threads"
    
