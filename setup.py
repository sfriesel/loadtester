from setuptools import setup

setup(
    name='loadtester',
    version='0.0.1',
    description='dirty little script to test loadbalancer performance',
    scripts=['loadtester.py'],
    install_requires=['urllib3', 'gevent'],
)
