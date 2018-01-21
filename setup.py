#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import os.path
import sys
import time
import subprocess
from setuptools import setup, find_packages, Command
from setuptools.command.test import test


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fp:
        return fp.read()


def readlines(fname):
    return [l.strip() for l in read(fname).strip().splitlines()]


def runcmd(cmd):
    with subprocess.Popen(
            cmd, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE) as p:
        out, err = p.communicate()
    return out, err


class PyTest(test):
    def finalize_options(self):
        super(PyTest, self).finalize_options()
        self.test_args = ['tests']
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


class GenerateVersionCommand(Command):
    description = 'generates a version file'
    user_options = [
        ('force=', 'f', 'force a specific version number')]

    def initialize_options(self):
        self.force = None

    def finalize_options(self):
        pass

    def run(self):
        v = self.force or generate_version()
        write_version(v)
        print("Generated version %s" % v)
        return 0


def generate_version():
    """ Generate a version file from the source control information.
        (this is loosely based on what Mercurial does)"""
    if os.path.isdir(os.path.join(os.path.dirname(__file__), '.hg')):
        return generate_version_from_mercurial()
    elif os.path.isdir(os.path.join(os.path.dirname(__file__), '.git')):
        return generate_version_from_git()
    else:
        raise Exception("Can't generate version number: this is not a "
                        "Mercurial repository.")


def generate_version_from_mercurial():
    try:
        # Get the version we're currently on. Also see if we have local
        # changes.
        cmd = ['hg', 'id', '-i']
        hgid, err = runcmd(cmd)
        hgid = hgid.decode('utf8').strip()
        has_local_changes = hgid.endswith('+')
        hgid = hgid.rstrip('+')

        # Get the tags on the current version.
        cmd = ['hg', 'log', '-r', '.', '--template', '{tags}\n']
        tags, err = runcmd(cmd)
        versions = [t for t in tags.decode('utf8').split() if t[0].isdigit()]

        if versions:
            # Use the tag found at the current revision.
            version = versions[-1]
        else:
            # Use the latest tag, but add info about how many revisions
            # there have been since then.
            cmd = ['hg', 'parents', '--template',
                   '{latesttag}+{latesttagdistance}']
            version, err = runcmd(cmd)
            tag, dist = version.decode('utf8').split('+')
            if dist == '1':
                # We're on the commit that created the tag in the first place.
                # Let's just do as if we were on the tag.
                version = tag
            else:
                version = '%s+%s.%s' % (tag, dist, hgid)

        if has_local_changes:
            if '+' in version:
                version += '.'
            else:
                version += '+'
            version += time.strftime('%Y%m%d')

        return version
    except OSError:
        raise Exception("Can't generate version number: Mercurial isn't "
                        "installed, or in the PATH.")
    except Exception as ex:
        raise Exception("Can't generate version number: %s" % ex)


def generate_version_from_git():
    try:
        cmd = ['git', 'describe', '--tags', '--dirty=+']
        version, err = runcmd(cmd)
        version = version.decode('utf8').strip()
        if version.endswith('+'):
            version += time.strftime('%Y%m%d')
        return version
    except OSError:
        raise Exception("Can't generate version number: Git isn't installed, "
                        "or in the PATH.")
    except Exception as ex:
        raise Exception("Can't generate version number: %s" % ex)


def write_version(version):
    if not version:
        raise Exception("No version to write!")

    f = open("piecrust/__version__.py", "w")
    f.write('# this file is autogenerated by setup.py\n')
    f.write('APP_VERSION = "%s"\n' % version)
    f.close()


try:
    from piecrust.__version__ import APP_VERSION
    version = APP_VERSION
except ImportError:
    print(
        "WARNING: Can't get version from version file. "
        "Will use version `0.0`.")
    version = '0.0'


install_requires = [
    'colorama>=0.3.3',
    'compressinja>=0.0.2',
    'Flask>=0.10.1',
    'Flask-IndieAuth>=0.0.3.2',
    'Flask-Login>=0.3.2',
    'Inukshuk>=0.1.1',
    'Jinja2>=2.9.6',
    'Markdown>=2.6.2',
    'MarkupSafe>=1.0',
    'misaka>=2.1.0',
    'paramiko>=2.0.0',
    'Pillow>=4.3.0',
    'Pygments>=2.0.2',
    'pystache>=0.5.4',
    'python-dateutil>=2.4.2',
    'PyYAML>=3.11',
    'repoze.lru>=0.6',
    'smartypants>=1.8.6',
    'strict-rfc3339>=0.5',
    'textile>=2.2.2',
    'Unidecode>=0.4.18',
    'watchdog>=0.8.3',
    'Werkzeug>=0.12.2'
]
tests_require = [
    'invoke>=0.21.0',
    'pytest>=2.8.7',
    'pytest-cov>=2.2.1',
    'pytest-mock>=0.10.1'
]


setup(
    name="PieCrust",
    version=version,
    description="A powerful static website generator and lightweight CMS.",
    long_description=read('README.rst') + '\n\n' + read('CHANGELOG.rst'),
    author="Ludovic Chabant",
    author_email="ludovic@chabant.com",
    license="Apache License 2.0",
    url="http://bolt80.com/piecrust",
    keywords=' '.join([
        'python',
        'website',
        'generator',
        'blog',
        'portfolio',
        'gallery',
        'cms'
    ]),
    packages=find_packages(exclude=['garcon', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_require,
    cmdclass={
        'test': PyTest,
        'version': GenerateVersionCommand
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP :: Site Management'
    ],
    entry_points={'console_scripts': [
        'chef = piecrust.main:main'
    ]}
)

