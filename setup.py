from setuptools import find_packages, setup

import versioneer

with open("Readme.md", "r") as fp:
    LONG_DESCRIPTION = fp.read()

setup(
    name="Kymion",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Simon-Martin Schroeder",
    author_email="martin.schroeder@nerdluecht.de",
    description="A Universal Progress Reporting Library",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/moi90/kymion",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=["attrs"],
    python_requires=">=3.9",
    extras_require={
        "tests": [
            "pytest",
            "pytest-cov",
            "codecov",
        ],
        "dev": ["versioneer[toml]"],
    },
    entry_points={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
    ],
)
