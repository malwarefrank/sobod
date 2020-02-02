import codecs
from os import path
from setuptools import setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with codecs.open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="sobod",
    version="0.5.0",
    description="Sequence Of Bytes On Disk",
    long_description=long_description,
    url="https://github.com/malwarefrank/sobod",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    packages=["sobod"],
    python_requires="~=3.5",
)
