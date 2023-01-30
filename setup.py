"""Install packages as defined in this file into the Python environment."""
from setuptools import setup, find_packages

setup(
    name="matplotlib_backend-kitty",
    author="geffk2",
    url="https://github.com/geffk2/matplotlib-backend-kitty",
    description="Fork of matplotlib-backend-kitty adapted for wezterm",
    version="0.1.0",
    packages=find_packages(where=".", exclude=["tests"]),
    install_requires=[
        "matplotlib",
    ],
)
