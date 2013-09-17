#!/usr/bin/env python
from distutils.core import setup


# django-static doesn't have a version but this setup.py does
VERSION = '1.5.5' # remember to match with django_static/__init__.py

import os
long_description = open(os.path.join(os.path.dirname(__file__),
                                     'README.rst')).read()


setup(
      name='django-static',
      version=VERSION,
      url='http://github.com/peterbe/django-static',
      download_url='http://pypi.python.org/pypi/django-static/',
      description='Template tags for better serving static files from templates in Django',
      long_description=long_description,
      author='Peter Bengtsson',
      author_email='peter@fry-it.com',
      platforms=['any'],
      license='BSD',
      packages=[
        'django_static',
        'django_static.templatetags',
        ],
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
)
