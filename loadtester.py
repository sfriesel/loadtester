#!/usr/bin/python2
import gevent.monkey
gevent.monkey.patch_all()
from threading import (
    Thread,
    Event,
)
from Queue import (
    Queue,
    Empty,
)
import time
import random
import sys
import socket
import itertools
from collections import namedtuple
import urllib3.connectionpool

DEFAULT_SCENARIO = [['/'], ['/fake.css', '/fake.png', '/fake.js'] * 10]


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
            self.run_scenario(DEFAULT_SCENARIO)
            self.event_queue.task_done()

    def handle_requests(self, request_queue, result_queue):
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
            if self.log_requests:
                request_end = time.time()
                self.test_env.requests_file.write(
                    '{browser_number} {start} {end} {status}\n'.format(
                        browser_number=int(self.name),
                        start=request_start - self.test_env.start_time,
                        end=request_end - self.test_env.start_time,
                        status=response.status))
            result_queue.put(response)
            request_queue.task_done()

    def run_scenario(self, scenario):
        request_queue = Queue()
        result_queue = Queue()
        requester = [Thread(target=self.handle_requests, args=(request_queue, result_queue)) for _ in range(6)]
        for req in requester:
            req.start()
        scenario_success = True
        self.pool = urllib3.connectionpool.HTTPConnectionPool(self.test_env.args.address, port=80, maxsize=6, block=True)
        scenario_start = time.time()
        for stage in scenario:
            for url in stage:
                request_queue.put(url)
            request_queue.join()
            while True:
                try:
                    response = result_queue.get_nowait()
                    if response.status != 200:
                        sys.stderr.write("got http code {0}\n".format(response.status))
                        scenario_success = False
                except Empty:
                    break
            if not scenario_success:
                break
        scenario_end = time.time()
        for req in requester:
            request_queue.put(None)
        if scenario_success:
            sys.stdout.write("{0} {1} 1\n".format(scenario_start - self.test_env.start_time, scenario_end - self.test_env.start_time))
        else:
            sys.stdout.write("{0} {1} 0\n".format(scenario_start - self.test_env.start_time, scenario_end - self.test_env.start_time))
            self.test_env.error_count += 1
        for req in requester:
            req.join()
        self.pool.close()
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
        self.event_queue.join()
        sys.stderr.write("error count: {0}\n".format(self.error_count))

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
    TestSetup(args).run()
