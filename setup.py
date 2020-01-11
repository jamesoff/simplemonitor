import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplemonitor",
    version="0.0.1",
    author="James Seward",
    author_email="james@jamesoff.net",
    description="A simple network and host monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jamesoff/simplemonitor",
    packages=setuptools.find_packages(exclude="tests"),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: No Input/Output (Daemon)",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Topic :: System :: Monitoring",
        "Typing :: Typed",
    ],
    python_requires=">=3.5",
    entry_points={"console_scripts": ["simplemonitor=simplemonitor.monitor:main"]},
    install_requires=[
        "requests",
        "boto3",
        "pyOpenSSL",
        "colorlog",
        "ring-doorbell",
        "paho-mqtt",
    ],
)
