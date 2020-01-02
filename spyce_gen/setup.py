from setuptools import setup

setup(
    name="spyce_gen",
    packages=["spyce_gen"],
    package_dir={ "spyce_gen": "" },
    entry_points={
        "console_scripts": ["spyce-gen=spyce_gen:main"]
    }
)