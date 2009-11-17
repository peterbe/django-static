#!/usr/bin/env python
from distutils.core import setup


# django-static doesn't have a version but this setup.py does
VERSION = '1.2'

README_FILE = open('README.md')
try:
    long_description = README_FILE.read()
finally:
    README_FILE.close()


setup(
      name='django-static',
      version=VERSION,
      url='http://github.com/peterbe/django-static',
      download_url='git://github.com/peterbe/django-static.git',
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

