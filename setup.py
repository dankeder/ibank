from setuptools import setup, find_packages
from subprocess import Popen, PIPE


def get_version():
    """
    Get version from PKG-INFO file.
    """
    try:
        # Try to get version from the PKG-INFO file
        f = open('PKG-INFO', 'r')
        for line in f.readlines():
            if line.startswith('Version: '):
                return line.split(' ')[1].strip()
    except IOError:
        # Try to get the version from the latest git tag
        p = Popen(['git', 'describe', '--tags'], stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip()

setup(name='ibank',
        version=get_version(),
        description='Bank statement downloader',
        long_description='Bank statement downloader',
        author='Dan Keder',
        author_email='dan.keder@gmail.com',
        url='http://github.com/dankeder/ibank',
        keywords='bank statement downloader citibank',
        packages=find_packages(),
        include_package_data=True,
        zip_safe=False,
        test_suite='ibank.tests',
        install_requires=[
                'docopt',
                'requests',
                'python-dateutil',
            ],
        entry_points={
                'console_scripts': [
                    'ibank-citibankcz = ibank.citibankcz:main',
                    'ibank-fio = ibank.fio:main'
                ]
            }
    )

# vim: expandtab

