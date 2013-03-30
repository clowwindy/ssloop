#!/usr/bin/env python
from setuptools import setup


setup(
    name='ssloop',
    version='0.0.1',
    packages=['ssloop'],
    package_data={
        'ssloop': ['README.md'],
    },
    install_requires=[],
    author='clowwindy',
    author_email='clowwindy42@gmail.com',
    url='http://github.com/clowwindy/ssloop',
    license='MIT',
    description='super lightweight event loop'
)
