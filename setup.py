from setuptools import setup, find_packages

setup(
    name='pipeek',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'pipeek = pipeek.__main__:main',
        ],
    },
)
