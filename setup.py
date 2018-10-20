from setuptools import setup, find_packages

with open('README.md') as f:
    long_description = f.read()

setup(
    name='pymidi',
    version='0.3.0',
    license='MIT',
    url='https://github.com/mik3y/pymidi',
    author='mike wakerly',
    author_email='opensource@hoho.com',
    description='Python RTP-MIDI / AppleMIDI driver',
    long_description=long_description,
    long_description_content_type='text/markdown',
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
