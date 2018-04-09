"""
Setup for hrepr
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='hrepr',
    version='0.1.6',

    description='Extensible HTML representation for Python objects.',
    long_description=long_description,

    url='https://github.com/breuleux/hrepr',

    author='Olivier Breuleux',
    author_email='breuleux@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    keywords='repr pprint html development',

    packages=find_packages(exclude=['contrib', 'doc', 'tests']),

    install_requires=[],

    extras_require={
        'dev': [],
        'test': [],
    },

    package_data={
        'hrepr': ['style/*.css'],
    },

    python_requires='>=3.6',
)
