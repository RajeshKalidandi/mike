"""Setup script for Mike.

Alternative installation method using setup.py for compatibility
with older tools and environments.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")
else:
    long_description = "Local AI software architect for private codebases"

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    requirements = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
else:
    requirements = [
        "tree-sitter>=0.20.0",
        "tree-sitter-languages>=1.5.0",
        "chromadb>=0.4.0",
        "pydantic>=2.0.0",
        "click>=8.0.0",
        "networkx>=3.0",
        "numpy>=1.24.0",
        "tqdm>=4.65.0",
    ]

setup(
    name="mike",
    version="0.1.0",
    author="Rajesh",
    author_email="rajesh@example.com",
    description="Local AI software architect for private codebases",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rajesh/mike",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
        "web": [
            "streamlit>=1.28.0",
        ],
        "embeddings": [
            "ollama>=0.1.0",
        ],
        "all": [
            "streamlit>=1.28.0",
            "ollama>=0.1.0",
            "rich>=13.0.0",
            "pyyaml>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "mike=mike.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
