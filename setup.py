"""
Setup module.
"""
from setuptools import setup

version = '1.0'

setup(
    name='lyricfetch',
    version=version,
    description='Fetch song lyrics from the internet',
    long_description='''Fetch lyrics from a variety of sources and save them as
        metadata into their corresponding mp3 files, or simply display them on
        the screen.''',
    url='https://github.com/ocaballeror/Lyricfetch',
    author='Oscar Caballero',
    author_email='ocaballeror@gmail.com',
    license='GNU General Public License, Version 3',
    classifiers=[
        'Environment :: Console',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    packages=['lyricfetch'],
    install_requires=[
        'urllib3>=1.22',
        'beautifulsoup4>=4.5.3',
        'eyeD3>=0.8.2',
    ],
    extras_require={
        'lint': [
            'flake8',
        ],
        'test': [
            'pytest',
            'pytest-xdist',
        ],
    },
)
