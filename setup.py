from setuptools import setup

setup(
    name = 'sphinx-csharp',
    version = '0.1.12',
    author = 'djungelorm',
    author_email = 'djungelorm@users.noreply.github.com',
    packages = ['sphinx_csharp'],
    url = 'https://github.com/djungelorm/sphinx-csharp',
    license = 'MIT',
    description = 'C# domain for Sphinx',
    python_requires = '>=3.11',
    install_requires = ['Sphinx>=9.0'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Programming Language :: Python :: 3.15',
        'Operating System :: OS Independent',
        'Topic :: Documentation :: Sphinx'
    ]
)
