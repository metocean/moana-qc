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
    setup(name = 'ops-core',
        version = get_package_version('ops_core'),
        description = 'Core library for MetOcean Actions',
        author='Ops Team',
        install_requires=getreq('requirements/default.txt'),
        test_require=getreq('requirements/tests.txt'),
        long_description=read('README.md'),
        test_suite='pytest',
        author_email='ops@metocean.co.nz',
        url='http://github.com/metocean/ops-core',
        packages=['ops_core'],
        entry_points={
            'console_scripts': [
                'run_action = ops_core.__main__:main',
            ],
        },
    )
