from setuptools import setup

setup(
    name = 'sphinx-csharp',
    version = '0.1.7',
    author = 'djungelorm',
    author_email = 'djungelorm@users.noreply.github.com',
    packages = ['sphinx_csharp'],
    url = 'https://github.com/djungelorm/sphinx-csharp',
    license = 'MIT',
    description = 'C# domain for Sphinx',
    install_requires = ['Sphinx>=1.6'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
        'Topic :: Documentation :: Sphinx'
    ]
)
