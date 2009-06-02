import os
import time
import re
from glob import glob
from base64 import decodestring
from unittest import TestCase

from django_static.templatetags.django_static import _static_file
def _slim_file(x, symlink_if_possible=False,):
    return _static_file(x, slimmer_if_possible=True,
                        symlink_if_possible=symlink_if_possible)

import settings 
#TEST_JS_FILENAME = '/test__django_slimmer.js'
#TEST_CSS_FILENAME = '/test__django_slimmer.css'
#TEST_GIF_FILENAME = '/test__django_slimmer.gif'

_GIF_CONTENT = 'R0lGODlhBgAJAJEDAGmaywBUpv///////yH5BAEAAAMALAAAAAAGAAkAAAIRnBFwITEoGoyBRWnb\ns27rBRQAOw==\n'
_GIF_CONTENT_DIFFERENT = 'R0lGODlhBAABAJEAANHV3ufr7qy9xGyiyCH5BAAAAAAALAAAAAAEAAEAAAIDnBAFADs=\n'

TEST_MEDIA_ROOT = '/tmp/fake_media_root'
_original_MEDIA_ROOT = settings.MEDIA_ROOT
_original_DEBUG = settings.DEBUG

class Test__django_slimmer(TestCase):
    
    def _notice_file(self, filepath):
        assert os.path.isfile(filepath)
        self.__added_filepaths.append(filepath)
        
    def setUp(self):
        self.__added_filepaths = []
        if not os.path.isdir(TEST_MEDIA_ROOT):
            os.mkdir(TEST_MEDIA_ROOT)
            
        super(Test__django_slimmer, self).setUp()
        
    def tearDown(self):
        for filepath in self.__added_filepaths:
            if os.path.isfile(filepath):
                os.remove(filepath)
        #if os.path.isfile(TEST_MEDIA_ROOT + TEST_JS_FILENAME):
        #    os.remove(TEST_MEDIA_ROOT + TEST_JS_FILENAME)
        #if os.path.isfile(TEST_MEDIA_ROOT + TEST_CSS_FILENAME):
        #    os.remove(TEST_MEDIA_ROOT + TEST_CSS_FILENAME)
        #if os.path.isfile(TEST_MEDIA_ROOT + TEST_GIF_FILENAME):
        #    os.remove(TEST_MEDIA_ROOT + TEST_GIF_FILENAME)
        
        # also remove any of the correctly generated ones
        for filepath in glob(TEST_MEDIA_ROOT + '/*'):
            os.remove(filepath)
        os.rmdir(TEST_MEDIA_ROOT)

        # restore things for other potential tests
        settings.MEDIA_ROOT = _original_MEDIA_ROOT
        settings.DEBUG = _original_DEBUG
        
        super(Test__django_slimmer, self).tearDown()


    def test__slim_file__debug_on_save_prefixed(self):
        """ test the private method _slim_file().
        We're going to assume that the file exists
        """
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_FILENAME = '/test.js'
        
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        result_filename = _slim_file(TEST_FILENAME)
        assert result_filename != TEST_FILENAME, "It hasn't changed"
        
        # the file should be called /test__django_slimmer.12345678.js
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
          .replace('/cache-forever', '')
        
        # The file will be stored in a different place than the 
        # TEST_MEDIA_ROOT
        # and the content should be slimmed
        self._notice_file(TEST_SAVE_PREFIX + result_filename)
        content = open(TEST_SAVE_PREFIX + result_filename).read()
        assert content == 'var a=test', content
        
        # run it again to test that the _slim_file() function can use
        # it's internal global variable map to get the file out
        assert result_filename == _slim_file(TEST_FILENAME)
        
        # if in debug mode, if the file changes and you call
        # _slim_file() it should return a new file and delete the
        # old one
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w').write('var b  =  foo\n')
        
        first_result_filename = result_filename
        result_filename = _slim_file(TEST_FILENAME)
        assert first_result_filename != result_filename, result_filename
        content = open(TEST_SAVE_PREFIX + result_filename).read()
        assert content == 'var b=foo', content
        
        # the previous file should have been deleted
        assert not os.path.isfile(TEST_SAVE_PREFIX + first_result_filename)
        
    def test__slim_file__debug_on_save_prefixed_name_prefixed(self):
        """ 
        If you use a name prefix it might have nothing to do with what the file
        is called or where it's found or where it's saved. By setting a name
        prefix you get something nice in your rendered HTML that you can use to
        split your rewrite rules in apache/nginx so that you can set different
        cache headers. 
        """
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_FILENAME = '/testtt.js'
        
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        result_filename = _slim_file(TEST_FILENAME)
        assert result_filename != TEST_FILENAME, "It hasn't changed"
        
        # the file should be called /test__django_slimmer.12345678.js
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
          .replace(TEST_NAME_PREFIX, '')
        
        # The file will be stored in a different place than the 
        # TEST_MEDIA_ROOT
        # and the content should be slimmed
        actual_saved_filepath = TEST_SAVE_PREFIX + \
          result_filename.replace(TEST_NAME_PREFIX, '')
        content = open(actual_saved_filepath).read()
        assert content == 'var a=test', content
        
        # run it again to test that the _slim_file() function can use
        # it's internal global variable map to get the file out
        assert result_filename == _slim_file(TEST_FILENAME)
        
        # if in debug mode, if the file changes and you call
        # _slim_file() it should return a new file and delete the
        # old one
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w').write('var b  =  foo\n')
        
        first_result_filename = result_filename
        result_filename = _slim_file(TEST_FILENAME)
        assert first_result_filename != result_filename, result_filename
        content = open(TEST_SAVE_PREFIX + \
                       result_filename.replace(TEST_NAME_PREFIX, '')).read()
        assert content == 'var b=foo', content
        
        # the previous file should have been deleted
        assert not os.path.isfile(TEST_MEDIA_ROOT + \
          first_result_filename.replace(TEST_NAME_PREFIX, ''))


    def test__static_file__debug_on_save_prefixed_name_prefixed_image(self):
        """ 
        Images are symlinked instead.
        """
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_FILENAME = '/example.gif'
        
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'wb')\
          .write(decodestring(_GIF_CONTENT))
        
        result_filename = _static_file(TEST_FILENAME, symlink_if_possible=True)
        assert result_filename != TEST_FILENAME, "It hasn't changed"
        
        # the file should be called /test__django_slimmer.12345678.js
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
          .replace(TEST_NAME_PREFIX, '')
        
        # The file will be stored in a different place than the 
        # TEST_MEDIA_ROOT
        # and the content should be slimmed
        actual_saved_filepath = TEST_SAVE_PREFIX + \
          result_filename.replace(TEST_NAME_PREFIX, '')
        content = open(actual_saved_filepath).read()
        assert content == decodestring(_GIF_CONTENT), content
        
        # run it again to test that the _static_file() function can use
        # it's internal global variable map to get the file out
        assert result_filename == _static_file(TEST_FILENAME,
                                               symlink_if_possible=True)
        
        # if in debug mode, if the file changes and you call
        # _static_file() it should return a new file and delete the
        # old one
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w').write(
          decodestring(_GIF_CONTENT_DIFFERENT))
        
        first_result_filename = result_filename
        result_filename = _static_file(TEST_FILENAME, 
                                       symlink_if_possible=True)
        assert first_result_filename != result_filename, result_filename
        content = open(TEST_SAVE_PREFIX + \
                       result_filename.replace(TEST_NAME_PREFIX, '')).read()
        assert content == decodestring(_GIF_CONTENT_DIFFERENT), content
        
        # the previous file should have been deleted
        assert not os.path.isfile(TEST_MEDIA_ROOT + \
          first_result_filename.replace(TEST_NAME_PREFIX, ''))



    def test__slim_file__debug_off(self):
        """ same test as test__slim_file__debug_on() but this time not
        in DEBUG mode. Then slimit will not notice that the file changes
        because it's more optimized. 
        """
        
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_FILENAME = '/foobar.css'
        
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        settings.DEBUG = False
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('body { color: #CCCCCC; }\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        result_filename = _slim_file(TEST_FILENAME)
        # the file should be called /test__django_slimmer.12345678.css
        timestamp = int(re.findall('\.(\d+)\.', result_filename)[0])
        now = int(time.time())
        # before we do the comparison, trim the last digit to prevent
        # bad luck on the millisecond and the rounding that int() does
        assert int(timestamp*.1) == int(now*.1)
        
        # if you remove that timestamp you should get the original 
        # file again
        assert TEST_FILENAME == \
          result_filename.replace(str(timestamp)+'.', '')\
                         .replace(TEST_NAME_PREFIX, '')
        
        
        # and the content should be slimmed
        actual_saved_filepath = TEST_SAVE_PREFIX + \
          result_filename.replace(TEST_NAME_PREFIX, '')
        content = open(actual_saved_filepath).read()
        assert content == 'body{color:#CCC}', content
            
        time.sleep(1) # slow but necessary
        # now change the original file
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('body { color:#FFFFFF}\n')
        
        result_filename = _slim_file(TEST_FILENAME)
        new_content = open(TEST_SAVE_PREFIX + \
            result_filename.replace(TEST_NAME_PREFIX,'')).read()
        assert new_content == content, new_content
            
        
    def test__slim_css_debug_on_save_prefixed_referring_urls(self):
        """ _slim_file() on a CSS that contains url(/local/image.gif)
        and the images should be _static_file()'ed too.
        """
        
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_SAVE_PREFIX = '/tmp/infinity'
        TEST_FILENAME = '/big.css'
        TEST_GIF_FILENAME = '/foo.gif'
        
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT

        open(TEST_MEDIA_ROOT + TEST_GIF_FILENAME, 'wb')\
          .write(decodestring(_GIF_CONTENT))
        self._notice_file(TEST_MEDIA_ROOT + TEST_GIF_FILENAME)
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('body { background:url(%s) }\n' % TEST_GIF_FILENAME)
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)

        result_filename = _slim_file(TEST_FILENAME, 
                                     symlink_if_possible=True)
        assert result_filename != TEST_FILENAME, "It hasn't changed"

        actual_saved_filepath = TEST_SAVE_PREFIX + \
          result_filename.replace(TEST_NAME_PREFIX, '')
        content = open(actual_saved_filepath).read()
        # The /foo.gif inside the converted content should now also 
        # have been transformed into /foo.123456789.gif
        start = 'body{background:url(%s%s' % \
          (TEST_NAME_PREFIX, os.path.splitext(TEST_GIF_FILENAME)[0])
        assert content.startswith(start), content
        expect = re.compile('/foo\.\d+\.gif')
        assert expect.findall(content), content

        