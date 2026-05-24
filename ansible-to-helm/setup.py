from setuptools import setup, find_packages

setup(
    name="ansible-to-helm",
    version="1.0.0",
    description="Generic Ansible to Helm Chart Converter Framework",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "PyYAML>=6.0",
        "Jinja2>=3.1",
        "click>=8.1",
        "jsonschema>=4.17",
        "rich>=13.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ansible-to-helm=converter.cli:main",
        ],
    },
)
