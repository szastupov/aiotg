from setuptools import setup, find_packages

version_file = open('VERSION')
version = version_file.read().strip()
version_file.close()

setup(
    name='aiotg',
    version=version,
    description='Asynchronous Python API for building Telegram bots',
    url='https://github.com/szastupov/aiotg',

    author='Stepan Zastupov',
    author_email='stepan.zastupov@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries'
    ],

    keywords='asyncio telegram',

    packages=find_packages(exclude=['examples', 'docs', 'tests*']),

    install_requires=['aiohttp>=1.0.0']
)
