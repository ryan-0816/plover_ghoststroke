#!/usr/bin/env python3
from setuptools import setup

if __name__ == "__main__":
    setup(
    name='plover-ghost-stroke',
    version='0.0.1',
    install_requires=['plover>=4.0.0'],
    entry_points={
        'plover.extension': [
            'ghost_stroke = your_module_name:GhostStroke'
            ],
        },
    )