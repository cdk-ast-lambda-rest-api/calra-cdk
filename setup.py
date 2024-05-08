from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='calra-cdk',

    version='0.2.7',

    description='CDK Ast Lambda Rest Api - CDK Package',
    long_description=long_description,

    url='https://github.com/cdk-ast-lambda-rest-api/calra-cdk',

    author='Mateo Marcos, Emanuel Arguinarena, Lucas Picchi',
        author_email='calra.github+mateo@gmail.com, calra.github+emanuel@gmail.com, calra.github+lucas@gmail.com',

    license='MIT',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Framework :: AWS CDK :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],

    keywords='cdk lambda aws api gateway ast',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
)
