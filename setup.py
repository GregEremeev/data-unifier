from setuptools import setup, find_packages


requirements = [r.strip() for r in open('requirements.txt').readlines() if '#' not in r]


setup(
    name='data-unifier',
    author='Greg Eremeev',
    author_email='gregory.eremeev@gmail.com',
    version='0.1.0',
    license='BSD-3-Clause',
    url='https://github.com/GregEremeev/data-unifier',
    install_requires=requirements,
    description='Toolset to unify data from different sources to one output',
    packages=find_packages(),
    extras_require={'dev': ['pdbpp>=0.10.2', 'pytest>=6.1.1', 'ipython>=7.18.1']},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    entry_points={
        'console_scripts': [
            'data_unifier = data_unifier.data_unifier:main',
        ]
    },
    zip_safe=False,
    include_package_data=True
)
