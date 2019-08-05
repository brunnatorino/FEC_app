import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="FEC-pkg-brunnatorino",
    version="0.0.1",
    author="Brunna Torino",
    author_email="torinobrunna@gmail.com",
    description="FEC package for French Auditing",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/brunnatorino/FEC",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
