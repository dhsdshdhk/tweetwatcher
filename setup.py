import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="tweetwatcher",
    version="0.0.3",
    author="John Doe",
    author_email="author@example.com",
    description="A simple tweet watcher.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dhsdshdhk/tweetwatcher",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points={
        'console_scripts': [
            'tweetwatcher=tweetwatcher.back:main',
            ],
        },
    python_requires='>=3.6',
    install_requires=['pyqt5', 'pandas', 'openpyxl']
)