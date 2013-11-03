"""
Flask-Window-Dressing
-------------

Window dressing for flask apps. Adds support for serializing responses
and deserializing requests (marshaling). Also adds support for different
resource representations.
"""
from setuptools import setup, find_packages


setup(
    name='Flask-Window-Dressing',
    version='0.1.0',
    url='https://github.com/rufman/Flask-Window-Dressing',
    license='MIT',
    author='Stephane Rufer',
    author_email='stephane.rufer@gmail.com',
    description='Cool thing to make Flask development easier',
    long_description=__doc__,
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask',
        'python-dateutil==2.1',
        'pytz',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
