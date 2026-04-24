from setuptools import find_packages, setup

setup(
    name="common-storage",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "boto3>=1.28.0",
        "pillow>=10.0.0",
    ],
)
