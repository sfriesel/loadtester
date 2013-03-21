#!/usr/bin/python2
from threading import (
    Thread,
    Event,
)
from Queue import Queue, Empty
import time
import random
import sys
import itertools
import socket
from socket import getaddrinfo


# Ugly hack to force ipv4
def force_ip4(*args, **kwargs):
    args = list(args)
    try:
        args[2] = socket.AF_INET
    except IndexError:
        pass
    if 'family' in kwargs:
        kwargs['family'] = socket.AF_INET
    return getaddrinfo(*args, **kwargs)

# replace the original socket.getaddrinfo by our version
socket.getaddrinfo = force_ip4
# End of ugly hack
import httplib2
import gevent.monkey
gevent.monkey.patch_all()

DOMAIN = sys.argv[1]

DEFAULT_SCENARIO = [['http://' + DOMAIN + '/'], ['http://' + DOMAIN + '/foo'] * 100]


class Browser(Thread):
    def __init__(self, test):
        Thread.__init__(self)
        self.daemon = True
        self.event_queue = test.event_queue
        self.test_env = test

    def run(self):
        while True:
            event_time = self.event_queue.get() + self.test_env.start_time
            #sys.stderr.write("{0}\n".format(self.event_queue.qsize()))
            # for now event is just the time when the next scenario should be run
            now = time.time()
            if now - 0.001 > event_time:
                sys.stderr.write("WARNING: missed event by {diff}s\n".format(diff=(now - event_time)))
            if now + 0.001 < event_time:
                time.sleep(event_time - now)
            self.run_scenario(DEFAULT_SCENARIO)
            self.event_queue.task_done()
            #sys.stderr.write("done {0}\n".format(resp_time))

    @staticmethod
    def handle_requests(request_queue, result_queue):
        http = httplib2.Http()
        while True:
            url = request_queue.get(block=True)
            if url is None:
                break
            response, content = http.request(url, headers={'Host': DOMAIN, 'Connection': 'keep-alive'})
            result_queue.put((response, content))
            request_queue.task_done()

    def run_scenario(self, scenario):
        request_queue = Queue()
        result_queue = Queue()
        requester = [Thread(target=self.handle_requests, args=(request_queue, result_queue)) for _ in range(6)]
        for req in requester:
            req.start()
        scenario_success = True
        scenario_start = time.time()
        for stage in scenario:
            for url in stage:
                request_queue.put(url)
            request_queue.join()
            while True:
                try:
                    response, _ = result_queue.get_nowait()
                    if response.status != 200:
                        sys.stderr.write("got http code {0}\n".format(response.status))
                        scenario_success = False
                except Empty:
                    break
            if not scenario_success:
                break
        scenario_end = time.time()
        if scenario_success:
            sys.stdout.write("{0} {1}\n".format(scenario_start - self.test_env.start_time, scenario_end - self.test_env.start_time))
        else:
            sys.stderr.write("scenario failed\n")
            self.test_env.error_count += 1
        for req in requester:
            request_queue.put(None)
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
    def __init__(self):
        self.event_queue = Queue()
        self.stopping = Event()
        self.browsers = [Browser(self) for _ in range(1000)]
        self.start_time = None
        self.error_count = 0

    def run(self):
        for browser in self.browsers:
            browser.start()
        #events = sorted(itertools.chain(gaussian_dist(num=900, duration=60, mean=30, stddev=10), uniform_dist(num=100, duration=60)))
        events = sorted(itertools.chain(uniform_dist(num=500, duration=60)))
        self.start_time = time.time()
        for event in events:
            self.event_queue.put(event)
        self.event_queue.join()
        sys.stderr.write("error count: {0}\n".format(self.error_count))

if __name__ == '__main__':
    TestSetup().run()
