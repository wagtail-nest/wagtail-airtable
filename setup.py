#!/usr/bin/env python

from setuptools import setup, find_packages

install_requires = [
    "wagtail>=2.6",
    "airtable-python-wrapper>=0.13.0",
    "djangorestframework>=3.11.0,<=3.12.2",
]

setup(
    name='wagtail-airtable',
    version='0.1.7',
    description="Sync data between Wagtail and Airtable",
    author='Kalob Taulien',
    author_email='kalob.taulien@torchbox.com',
    url='https://github.com/wagtail/wagtail-airtable',
    packages=find_packages(exclude=('tests',)),
    include_package_data=True,
    license='BSD',
    long_description="An extension for Wagtail allowing content to be transferred between Airtable sheets and your Wagtail/Django models",
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Framework :: Django',
        'Framework :: Wagtail',
        'Framework :: Wagtail :: 2',
    ],
    install_requires=install_requires,
)
