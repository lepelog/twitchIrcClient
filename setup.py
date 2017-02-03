from setuptools import setup

with open("twitchircclient/.version") as f:
    version = f.read().strip()

setup(
    name='twitchircclient',
    version=version,
    packages=['twitchircclient'],
    include_package_data=False,
    install_requires=[]
)
