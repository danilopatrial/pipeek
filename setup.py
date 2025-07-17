from setuptools import setup, find_packages

from setuptools import setup, find_packages

setup(
    name="pipeek",
    version="0.1.0",
    description="A search tool for compressed and uncompressed files.",
    author="Danilo Patrial",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "colorama",
        "click",
        "platformdirs"
    ],
    entry_points={
        "console_scripts": [
            "pipeek = pipeek.__main__:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires=">=3.8",
)
