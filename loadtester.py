#!/usr/bin/python2
import gevent.monkey
gevent.monkey.patch_all()
import gevent
import gevent.pool
import time
import random
import sys
import socket
import itertools
from collections import namedtuple
import urllib3.connectionpool
import urllib3.exceptions


class Browser(gevent.Greenlet):
    def __init__(self, test, delay, **kwargs):
        gevent.Greenlet.__init__(self, **kwargs)
        self.name = '0'
        self.test_env = test
        self.delay = delay
        self.log_requests = bool(self.test_env.requests_file)
        self.pool = None

    def run(self):
        event_time = self.delay + self.test_env.start_time
        # for now event is just the time when the next scenario should be run
        now = time.time()
        if abs(now - event_time) > 0.01:
            sys.stderr.write("WARNING: missed event by {diff}s\n".format(diff=(now - event_time)))
        scenario_start = time.time()
        self.pool = urllib3.connectionpool.HTTPConnectionPool(self.test_env.args.address, port=80, maxsize=6, block=True)
        scenario_success = self.make_request('/')
        scenario_end = time.time()
        sys.stdout.write("{0} {1} {2}\n".format(scenario_start - self.test_env.start_time, scenario_end - self.test_env.start_time, int(scenario_success)))
        if not scenario_success:
            self.test_env.error_count += 1
        self.pool.close()

    def make_request(self, url):
        if self.log_requests:
            request_start = time.time()
        try:
            response = self.pool.urlopen('GET', url, headers={
                'Host': self.test_env.args.host or self.test_env.args.address,
                'Connection': 'keep-alive',
                'User-Agent': 'sfloadtester'})
        except (socket.error, urllib3.exceptions.HTTPError) as e:
            response = namedtuple(typename='SocketErrorResponse', field_names=['status', 'exception'])(status=str(e), exception=e)

        if self.log_requests:
            request_end = time.time()
            self.test_env.requests_file.write(
                '{browser_number} {start} {end} {status}\n'.format(
                    browser_number=int(self.name),
                    start=request_start - self.test_env.start_time,
                    end=request_end - self.test_env.start_time,
                    status=response.status))

        if response.status == 200 and response.getheader('content-type').startswith('text/'):
            subresults = gevent.pool.Group().imap(self.make_request, iter(iter(response.data.split('\n')).next, ''))
        else:
            subresults = []

        if response.status != 200:
            sys.stderr.write(url + " got http code {0}\n".format(response.status))

        return response.status == 200 and all(subresults)


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
        self.start_time = None
        self.error_count = 0
        self.args = args
        self.requests_file = open(self.args.requests_file[0], 'wb') if self.args.requests_file else None
        self.browsers = gevent.pool.Group()

    def run(self):
        events_iter = itertools.chain(uniform_dist(num=self.args.uniform * self.args.duration / 60, duration=self.args.duration))
        self.start_time = self.args.start_time or time.time()
        for delay in events_iter:
            browser = Browser(self, delay)
            self.browsers.add(browser)
            browser.start_later(max(0, self.start_time + delay - time.time()))
        self.browsers.join(timeout=self.args.duration + 60, raise_error=True)
        self.browsers.kill(exception=RuntimeError)
        self.browsers.join(timeout=2, raise_error=True)
        sys.stderr.write("error count: {0}\n".format(self.error_count))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Loadtest a website with a somewhat realistic access pattern.')
    parser.add_argument('--duration', default=60, type=int, help='test duration in seconds')
    parser.add_argument('--uniform', default=600, type=int, help='uniformly distributed sessions per minute')
    parser.add_argument('--start-time', type=float, help='time when to start the test (unix timestamp)')
    parser.add_argument('--host', help='value of host header (default is domain)')
    parser.add_argument('--requests-file', metavar='FILE', nargs=1, help='in addition to normal output, log every single request to FILE')
    parser.add_argument('address', help='the address to connect to')

    args = parser.parse_args()

    TestSetup(args).run()
