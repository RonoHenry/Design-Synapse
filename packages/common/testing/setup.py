from setuptools import find_packages, setup

setup(
    name="common-testing",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "factory-boy>=3.3.0",
        "faker>=20.0.0",
    ],
)
