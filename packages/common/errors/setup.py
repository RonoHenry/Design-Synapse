from setuptools import find_packages, setup

setup(
    name="common-errors",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
    ],
)
