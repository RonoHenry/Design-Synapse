from setuptools import find_packages, setup

setup(
    name="common-monitoring",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.100.0",
        "prometheus-client>=0.17.0",
        "python-json-logger>=2.0.0",
    ],
)
