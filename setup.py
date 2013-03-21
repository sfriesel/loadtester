from setuptools import setup

setup(
    name='sfloadtester',
    version='0.0.1',
    description='dirty little script to test loadbalancer performance',
    author='Stefan Friesel',
    scripts=['loadtester.py'],
    install_requires=['urllib3', 'gevent'],
)
