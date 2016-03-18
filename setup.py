"""
 asr-pipeline
A software pipeline for aligning sequences, inferring ML phylogenies,
reconstructing ancestors, and more
"""

import sys
from setuptools import setup, find_packages
from glob import glob

extra = {}
if sys.version_info >= (3, 0):
    extra.update(
        use_2to3=True,
    )

setup(
    name="asr-pipeline",
    version="0.2",
    packages=find_packages(),
    scripts=glob('./scripts/*'),
    zip_safe=True,
    platforms=["Linux", "Mac OS-X", "Unix"],
    author="Victor Hanson-Smith",
    author_email="victor.hanson-smith@ucsf.edu",
    description="A software pipeline for aligning sequences, inferring ML phylogenies, reconstructing ancestors, and more",
    keywords="ancestral sequence reconstruction",
    url="https://github.com/vhsvhs/asr-pipeline",
    **extra
)
