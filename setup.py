#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=7.0',
    'pandas>=1.0.0',
    'tqdm>=4.46.0',
    'inflection>=0.4.0',
    'gpxpy>=1.4.0',
    'geopy>=1.22.0',
    'importlib_resources ; python_version<"3.7"'
]

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest>=3', 'coverage>=5.1']

setup(
    author="Merelda Wu",
    author_email='merelda@melio.co.za',
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="A library to parse, wrangle and plot Apple Health data.",
    entry_points={
        'console_scripts': [
            'ipyhealth=ipyhealth.cli:main',
        ],
    },
    install_requires=requirements,
    extra_require={
        'dev': [
            'flake8',
            'pylint',
            'pytest',
            'pytest-runner'
        ]
    },
    license="MIT license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='ipyhealth',
    name='ipyhealth',
    packages=find_packages(include=['ipyhealth', 'ipyhealth.*']),
    package_data={'ipyhealth': ['templates/*json']},
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/mereldawu/ipyhealth',
    version='0.1.1',
    zip_safe=False,
)
