#!/usr/bin/python2
import gevent.monkey
gevent.monkey.patch_all()
from threading import Thread, Event, Timer
from Queue import Queue, Empty
import time
import random
import sys
import socket
import itertools
from collections import namedtuple
import urllib3.connectionpool


class Browser(Thread):
    def __init__(self, test, **kwargs):
        Thread.__init__(self, **kwargs)
        self.daemon = True
        self.event_queue = test.event_queue
        self.test_env = test
        self.log_requests = bool(self.test_env.requests_file)
        self.pool = None

    def run(self):
        while True:
            event_time = self.event_queue.get() + self.test_env.start_time
            # for now event is just the time when the next scenario should be run
            now = time.time()
            if now - 0.001 > event_time:
                sys.stderr.write("WARNING: missed event by {diff}s\n".format(diff=(now - event_time)))
            if now + 0.001 < event_time:
                time.sleep(event_time - now)
            self.run_scenario()
            self.event_queue.task_done()

    def handle_requests(self, request_queue, scenario_failed):
        while True:
            url = request_queue.get(block=True)
            if url is None:
                break
            if self.log_requests:
                request_start = time.time()
            try:
                response = self.pool.urlopen('GET', url, headers={
                    'Host': self.test_env.args.host or self.test_env.args.address,
                    'Connection': 'keep-alive',
                    'User-Agent': 'sfloadtester'})
            except socket.error as e:
                response = namedtuple(typename='SocketErrorResponse', field_names=['status', 'exception'])(status=str(e), exception=e)
            else:
                if response.status == 200 and response.getheader('content-type').startswith('text/'):
                    content = response.data
                    for line in content.split('\n'):
                        if line == '':
                            break
                        else:
                            request_queue.put(line.rstrip())

            if self.log_requests:
                request_end = time.time()
                self.test_env.requests_file.write(
                    '{browser_number} {start} {end} {status}\n'.format(
                        browser_number=int(self.name),
                        start=request_start - self.test_env.start_time,
                        end=request_end - self.test_env.start_time,
                        status=response.status))

            if response.status != 200:
                sys.stderr.write(url + " got http code {0}\n".format(response.status))
                scenario_failed.set()
            request_queue.task_done()

    def run_scenario(self):
        request_queue = Queue()
        scenario_failed = Event()
        requester = [Thread(target=self.handle_requests, args=(request_queue, scenario_failed)) for _ in range(6)]
        for req in requester:
            req.start()
        scenario_start = time.time()
        if self.pool:
            self.pool.close()
        self.pool = urllib3.connectionpool.HTTPConnectionPool(self.test_env.args.address, port=80, maxsize=6, block=True)
        request_queue.put('/')
        request_queue.join()
        scenario_end = time.time()
        for req in requester:
            request_queue.put(None)
        sys.stdout.write("{0} {1} {2}\n".format(scenario_start - self.test_env.start_time, scenario_end - self.test_env.start_time, int(not scenario_failed.is_set())))
        if scenario_failed.is_set():
            self.test_env.error_count += 1
        for req in requester:
            req.join()
        return scenario_end - scenario_start


def gaussian_dist(num, duration, mean, stddev):
    for _ in range(10 * num):
        if not num:
            break
        value = random.gauss(mean, stddev)
        if value >= 0 and value < duration:
            num -= 1
            yield value
    else:
        raise Exception("failed to generate requested distribution")


def uniform_dist(num, duration):
    for _ in range(num):
        yield random.uniform(0, duration)


class TestSetup(object):
    def __init__(self, args):
        self.event_queue = Queue()
        self.stopping = Event()
        self.start_time = None
        self.error_count = 0
        self.args = args
        self.requests_file = open(self.args.requests_file[0], 'wb') if self.args.requests_file else None
        self.browsers = [Browser(self, name=str(i)) for i in range(self.args.browsers)]

    def run(self):
        for browser in self.browsers:
            browser.start()
        events = sorted(itertools.chain(uniform_dist(num=self.args.uniform * self.args.duration / 60, duration=self.args.duration)))
        self.start_time = self.args.start_time or time.time()
        for event in events:
            self.event_queue.put(event)
        print "queue put", time.time() - self.start_time
        self.event_queue.join()
        sys.stderr.write("error count: {0}\n".format(self.error_count))

    def stop(self, exception=None):
        sys.stderr.write("Forced exit")
        if exception:
            sys.stderr.write("An exception occured:\n")
            sys.stderr.write(exception)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Loadtest a website with a somewhat realistic access pattern.')
    parser.add_argument('--browsers', default=150, type=int, help='maximum number of virtual browsers (fd limit!)')
    parser.add_argument('--duration', default=60, type=int, help='test duration in seconds')
    parser.add_argument('--uniform', default=600, type=int, help='uniformly distributed sessions per minute')
    parser.add_argument('--start-time', type=float, help='time when to start the test (unix timestamp)')
    parser.add_argument('--host', help='value of host header (default is domain)')
    parser.add_argument('--requests-file', metavar='FILE', nargs=1, help='in addition to normal output, log every single request to FILE')
    parser.add_argument('address', help='the address to connect to')

    args = parser.parse_args()

    testSetup = TestSetup(args)
    Timer(args.duration + 4 * 60, testSetup.stop)
    try:
        testSetup.run()
    except Exception as e:
        testSetup.stop(e)
