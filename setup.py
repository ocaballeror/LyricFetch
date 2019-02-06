"""
Setup module.
"""
import re
from os.path import join
from setuptools import setup

with open(join('lyricfetch', '__init__.py')) as f:
    line = next(l for l in f if l.startswith('__version__'))
    version = re.match('__version__ = [\'"]([^\'"]+)[\'"]', line).group(1)

setup(
    name='lyricfetch',
    version=version,
    description='Fetch song lyrics from the internet',
    long_description="""Fetch lyrics from a variety of sources and save them as
        metadata into their corresponding mp3 files, or simply display them on
        the screen.""",
    url='https://github.com/ocaballeror/Lyricfetch',
    author='Oscar Caballero',
    author_email='ocaballeror@gmail.com',
    license='GNU General Public License, Version 3',
    classifiers=[
        'Environment :: Console',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    packages=['lyricfetch'],
    package_data={
        'lyricfetch': ['config.json']
    },
    include_package_data=True,
    entry_points={
        'console_scripts': ['lyricfetch=lyricfetch.cli:main']
    },
    python_requires='>=3.6',
    install_requires=[
        'urllib3>=1.22',
        'beautifulsoup4>=4.5.3',
        'eyeD3>=0.8.2',
        'jeepney>=0.4',
    ],
    extras_require={
        'lint': [
            'flake8',
            'flake8-quotes',
        ],
        'test': [
            'tox',
            'pytest',
            'pytest-cov',
        ],
    },
)
