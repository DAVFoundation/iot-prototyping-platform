from setuptools import setup

setup(
    name = 'mooving_iot',
    version = '0.0.1',
    packages = ['mooving_iot'],
    entry_points = {
        'console_scripts': [
            'mooving_iot = mooving_iot.__main__:main'
        ]
    }
)
