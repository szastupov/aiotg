from setuptools import setup, find_packages

setup(
    name='aiotg',
    version='0.7.7',
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

    install_requires=['aiohttp>=0.17.2']
)
