import os
import re

from setuptools import setup

HERE = os.path.dirname(os.path.abspath(__file__))
version = re.compile(r'(?<=__version__\s=\s).+')

def get_package_version(package_dir):
    "returns package version without importing it"
    with open(os.path.join(HERE, package_dir,"__init__.py")) as initf:
        return version.search(initf.readlines()[0]).group().strip("'")

def read(fname):
    with open(os.path.join(HERE, fname)) as openfile:
        return openfile.read()

def getreq(fpath):
    return read(fpath).splitlines()

if __name__ == '__main__':
    setup(name = 'ops_qc',
        version = get_package_version('ops_qc'),
        description = 'Quality Control Library for Manogpare Sensor',
        author='Ops Team - Julie Jakoboski',
        install_requires=getreq('requirements/default.txt'),
        test_require=getreq('requirements/tests.txt'),
        long_description=read('README.md'),
        test_suite='pytest',
        author_email='ops@metocean.co.nz',
        url='http://github.com/metocean/ops-qc',
        packages=['ops_qc'],
    )
