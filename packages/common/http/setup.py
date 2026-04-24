from setuptools import find_packages, setup

setup(
    name="common-http",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.25.0",
        "fastapi>=0.100.0",
    ],
)
