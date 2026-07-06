from setuptools import setup, find_packages

import os

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "upt_guardian", "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="upt-guardian",
    version="1.0.0",
    description="Advanced Global Disaster Monitoring & Quantum Reactor Stability AI Engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Võ Trần Hoàng Uy",
    author_email="vtuy2004@gmail.com",
    packages=find_packages(include=["upt_guardian", "upt_guardian.*"]),
    install_requires=[
        "numpy",
        "scikit-learn",
        "tensorflow>=2.15.0",
        "global-land-mask"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
