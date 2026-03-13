from setuptools import setup, find_packages

# Read the requirements from the requirements.txt file
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="template",
    version="0.1.0",
    author="Mayank Kumar",
    author_email="mayank@deeptempo.ai",
    description="Template repository for pipeline support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/DeepTempo/template",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
