#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from pathlib import Path

# Read README with explicit UTF-8 encoding (fixes Windows GBK error)
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

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
    description="A minimalist CLI Agent framework — the best textbook for understanding AI Agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ZhuLinsen/MiniAgent",
    project_urls={
        "Bug Tracker": "https://github.com/ZhuLinsen/MiniAgent/issues",
        "Source": "https://github.com/ZhuLinsen/MiniAgent",
    },
    keywords=["agent", "ai", "llm", "cli", "tool-calling", "miniagent", "deepseek", "openai"],
    license="Apache-2.0",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "miniagent=miniagent.cli:main",
        ]
    },
) 