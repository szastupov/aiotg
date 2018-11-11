# yapf: disable
from setuptools import setup, find_packages

version_file = open('VERSION')
version = version_file.read().strip()
version_file.close()

setup(
    name='aiotg',
    version=version,
    description='Asynchronous Python API for building Telegram bots',
    url='http://szastupov.github.io/aiotg',

    author='Stepan Zastupov',
    author_email='stepan.zastupov@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries'
    ],

    keywords='asyncio telegram',

    packages=find_packages(exclude=['examples', 'docs', 'tests*']),

    install_requires=['aiohttp>=3.0.0', 'aiosocksy>=0.1.1', 'watchdog>=0.9.0'],
    setup_requires=['pytest-runner', 'flake8'],
    tests_require=['pytest', 'testfixtures']
)
