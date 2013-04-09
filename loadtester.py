#!/usr/bin/python2
import gevent.monkey
gevent.monkey.patch_all()
import gevent
import gevent.pool
import time
import random
import sys
import signal
import socket
import itertools
from collections import namedtuple
import urllib3.connectionpool
import urllib3.exceptions


class Browser(gevent.Greenlet):
    def __init__(self, test, delay, **kwargs):
        gevent.Greenlet.__init__(self, **kwargs)
        self.test_env = test
        self.delay = delay
        self.log_requests = bool(self.test_env.requests_file)
        self.pool = None

    def _run(self):
        event_time = self.delay + self.test_env.start_time
        scenario_start = time.time()
        if abs(scenario_start - event_time) > 0.05:
            sys.stderr.write("WARNING: missed event {event} by {diff}s\n".format(event=self.delay, diff=(scenario_start - event_time)))
        self.pool = urllib3.connectionpool.HTTPConnectionPool(self.test_env.args.address, port=80, maxsize=6, block=True)
        try:
            scenario_success = self.make_request('/')
        except RuntimeError:
            scenario_success = False
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
                'User-Agent': 'sfloadtester'},
                timeout=65,
                pool_timeout=65,
                retries=0)
        except (socket.error, urllib3.exceptions.HTTPError) as e:
            response = namedtuple(typename='SocketErrorResponse', field_names=['status', 'exception'])(status=str(e), exception=e)

        if self.log_requests:
            request_end = time.time()
            self.test_env.requests_file.write(
                '{browser_number} {start} {end} {status}\n'.format(
                    browser_number=0,
                    start=request_start - self.test_env.start_time,
                    end=request_end - self.test_env.start_time,
                    status=response.status))

        if response.status == 200 and response.getheader('content-type').startswith('text/'):
            subresults = gevent.pool.Group().imap(self.make_request, iter(iter(response.data.split('\n')).next, ''))
        else:
            subresults = []

        if response.status != 200:
            sys.stderr.write("{time} {url} got http code {code}\n".format(time=time.time() - self.test_env.start_time, url=url, code=response.status))

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
        events_iter = itertools.chain(uniform_dist(num=self.args.uniform * self.args.duration / 60,
                                                   duration=self.args.duration),
                                      gaussian_dist(num=self.args.gauss * self.args.duration / 60,
                                                    duration=self.args.duration,
                                                    mean=self.args.duration / 3,
                                                    stddev=self.args.duration / 8))
        self.start_time = self.args.start_time or time.time()
        for delay in events_iter:
            browser = Browser(self, delay)
            self.browsers.add(browser)
            browser.start_later(max(0, self.start_time + delay - time.time()))
        self.browsers.join(timeout=self.args.duration + 600, raise_error=True)
        if len(self.browsers):
            self.browsers.kill(exception=RuntimeError)
            self.browsers.join(timeout=2, raise_error=True)
            raise Exception('deadlock')
        else:
            sys.stderr.write("error count: {0}\n".format(self.error_count))

    def term(self):
        self.browsers.kill(exception=RuntimeError)
        self.browsers.join(timeout=2, raise_error=True)
        raise Exception('killed by signal')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Loadtest a website with a somewhat realistic access pattern.')
    parser.add_argument('--duration', default=60, type=int, help='test duration in seconds')
    parser.add_argument('--uniform', default=600, type=int, help='uniformly distributed sessions per minute')
    parser.add_argument('--gauss', default=0, type=int, help='gaussian distributed sessions per minute')
    parser.add_argument('--start-time', type=float, help='time when to start the test (unix timestamp)')
    parser.add_argument('--host', help='value of host header (default is domain)')
    parser.add_argument('--requests-file', metavar='FILE', nargs=1, help='in addition to normal output, log every single request to FILE')
    parser.add_argument('address', help='the address to connect to')

    args = parser.parse_args()

    s = TestSetup(args)
    signal.signal(signal.SIGTERM, s.term)
    s.run()
