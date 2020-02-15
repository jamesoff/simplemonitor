import setuptools

from simplemonitor.version import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simplemonitor",
    version=VERSION,
    author="James Seward",
    author_email="james@jamesoff.net",
    description="A simple network and host monitor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jamesoff/simplemonitor",
    packages=setuptools.find_packages(exclude="tests"),
    package_data={
        "simplemonitor": ["html/header.html", "html/footer.html", "html/style.css"]
    },
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
    entry_points={
        "console_scripts": [
            "simplemonitor=simplemonitor.monitor:main",
            "winmonitor=simplemonitor.winmonitor:main",
        ]
    },
    extras_require={"ring": ["ring-doorbell>=0.6.0"]},
    install_requires=[
        "requests",
        "boto3",
        "pyOpenSSL",
        "colorlog",
        "paho-mqtt",
        'pync; platform_system=="Darwin"',
        'pywin32; platform_system=="Windows"',
    ],
)
