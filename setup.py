from setuptools import setup

setup(
    name = 'sphinx-csharp',
    version = '0.1.3',
    author = 'djungelorm',
    author_email = 'djungelorm@users.noreply.github.com',
    packages = ['sphinx_csharp'],
    url = 'https://github.com/djungelorm/sphinx-csharp',
    license = 'MIT',
    description = 'C# domain for Sphinx',
    install_requires = ['Sphinx'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Operating System :: OS Independent',
        'Topic :: Documentation :: Sphinx'
    ]
)
