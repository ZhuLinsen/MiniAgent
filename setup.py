#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name="miniagent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=0.19.0",
        "tenacity>=8.0.0",
        "requests>=2.31.0",
        "psutil>=5.9.0",
        "distro>=1.8.0",
        "rich>=13.0.0",
    ],
    author="MiniAgent Team",
    author_email="miniagent@example.com",
    description="A lightweight Agent framework supporting tool calls and self-reflection",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ZhuLinsen/MiniAgent",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "miniagent=miniagent.cli:main",
            "miniagent-gui=miniagent.gui:main",
        ]
    },
) 