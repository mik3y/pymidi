from setuptools import setup, find_packages

setup(
    name='pymidi',
    version='0.1.0',
    license='MIT',
    url='https://github.com/mik3y/pymidi',
    author='mike wakerly',
    author_email='opensource@hoho.com',
    description='Python RTP-MIDI / AppleMIDI driver',
    packages=find_packages(),
    install_requires=[
        'construct >= 2.9',
    ],
    test_suite='nose.collector',
    tests_require=[
        'nose',
        'flake8',
    ],
)
