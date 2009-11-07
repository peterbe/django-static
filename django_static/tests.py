import os
import stat
import time
import re
from tempfile import mkdtemp, gettempdir
from glob import glob
from base64 import decodestring
from unittest import TestCase
from shutil import rmtree
import warnings

from django_static.templatetags.django_static import _static_file, _combine_filenames
def _slim_file(x, symlink_if_possible=False,):
    return _static_file(x, slimmer_if_possible=True,
                        symlink_if_possible=symlink_if_possible)

try:
    from slimmer import css_slimmer, guessSyntax, html_slimmer, js_slimmer
    slimmer = 'installed'
except ImportError:
    slimmer = None
    import warnings
    warnings.warn("Can't run tests that depend on slimmer")


from django.conf import settings 
from django.template import Template
from django.template import Context
        
_GIF_CONTENT = 'R0lGODlhBgAJAJEDAGmaywBUpv///////yH5BAEAAAMALAAAAAAGAAkAAAIRnBFwITEoGoyBRWnb\ns27rBRQAOw==\n'
_GIF_CONTENT_DIFFERENT = 'R0lGODlhBAABAJEAANHV3ufr7qy9xGyiyCH5BAAAAAAALAAAAAAEAAEAAAIDnBAFADs=\n'

TEST_MEDIA_ROOT = '/tmp/fake_media_root'
_original_MEDIA_ROOT = settings.MEDIA_ROOT
_original_DEBUG = settings.DEBUG
_original_DJANGO_STATIC_SAVE_PREFIX = getattr(settings, 'DJANGO_STATIC_SAVE_PREFIX', '')
_original_DJANGO_STATIC_NAME_PREFIX = getattr(settings, 'DJANGO_STATIC_NAME_PREFIX', '')
_original_DJANGO_STATIC_MEDIA_URL = getattr(settings, 'DJANGO_STATIC_MEDIA_URL', '')

class TestDjangoStatic(TestCase):
    
    def _notice_file(self, filepath):
        assert os.path.isfile(filepath)
        self.__added_filepaths.append(filepath)
        
    def setUp(self):
        self.__added_filepaths = []
        if not os.path.isdir(TEST_MEDIA_ROOT):
            os.mkdir(TEST_MEDIA_ROOT)
            
        self._temp_directory = mkdtemp()
        assert self._temp_directory.startswith(gettempdir())
        
        super(TestDjangoStatic, self).setUp()
        
    def tearDown(self):
        for filepath in self.__added_filepaths:
            if os.path.isfile(filepath):
                os.remove(filepath)
                
        # also remove any of the correctly generated ones
        rmtree(TEST_MEDIA_ROOT)
        #for filepath in glob(TEST_MEDIA_ROOT + '/*'):
        #    if os.path.isfile(filepath):
        #        os.remove(filepath)
        #    elif os.path.isdir(filepath):
        #        for sub_filepath in glob(filepath):
        #            if os.path.isfile(
        #        os.rmdir(filepath)
        #os.rmdir(TEST_MEDIA_ROOT)

        # restore things for other potential tests
        settings.MEDIA_ROOT = _original_MEDIA_ROOT
        settings.DEBUG = _original_DEBUG
        settings.DJANGO_STATIC_SAVE_PREFIX = _original_DJANGO_STATIC_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = _original_DJANGO_STATIC_NAME_PREFIX
        settings.DJANGO_STATIC_MEDIA_URL = _original_DJANGO_STATIC_MEDIA_URL
        
        assert self._temp_directory.startswith(gettempdir())
        rmtree(self._temp_directory)
        
        super(TestDjangoStatic, self).tearDown()


    def test__slim_file__debug_on_save_prefixed(self):
        """ test the private method _slim_file().
        We're going to assume that the file exists
        """
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
        TEST_FILENAME = '/test.js'

        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        if slimmer is None:
            return
        
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
        time.sleep(1.1) # slow but necessary
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
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_FILENAME = '/testtt.js'
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        if slimmer is None:
            return
        
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
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
        TEST_NAME_PREFIX = '/cache-forever'
        TEST_FILENAME = '/example.gif'
        
        settings.DEBUG = True
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
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
        TEST_FILENAME = '/foobar.css'
        
        settings.DJANGO_STATIC = True        
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = TEST_NAME_PREFIX
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        settings.DEBUG = False
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('body { color: #CCCCCC; }\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)
        
        if slimmer is None:
            return
        
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
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
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

        if slimmer is None:
            return 
        
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

        
    def test_slimfile_with_media_url(self):
        """ same as test__slim_file__debug_on_save_prefixed
        but this time with DJANGO_STATIC_MEDIA_URL set.
        """
        TEST_SAVE_PREFIX = os.path.join(self._temp_directory, 'infinity')
        TEST_FILENAME = '/test.js'

        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME)

        template_as_string = """
        {% load django_static %}
        {% slimfile "/test.js" %}
        """
        # First do it without DJANGO_STATIC_MEDIA_URL set
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        
        expect_mtime = os.stat(TEST_MEDIA_ROOT + TEST_FILENAME)[stat.ST_MTIME]
        expect_rendered = u'/test.%d.js' % expect_mtime
        self.assertEqual(rendered, expect_rendered)
        
        settings.DJANGO_STATIC_MEDIA_URL = 'http://static.example.com'
        
        rendered = template.render(context).strip()
        expect_rendered = u'http://static.example.com/test.%d.js' % expect_mtime
        self.assertEqual(rendered, expect_rendered)
        
        # this should work if you change the file
        time.sleep(1)
        open(TEST_MEDIA_ROOT + TEST_FILENAME, 'w')\
          .write('var a  =  different\n')
        expect_mtime = os.stat(TEST_MEDIA_ROOT + TEST_FILENAME)[stat.ST_MTIME]
        
        rendered = template.render(context).strip()
        expect_rendered = u'http://static.example.com/test.%d.js' % expect_mtime
        self.assertEqual(rendered, expect_rendered)
        
    def test_slimcontent(self):
        """test to run the slimcontent tag which slims everything between
        {% slimcontent %}
        ...and...
        {% endslimcontent %}
        """
        if slimmer is None:
            return
        
        template_as_string = """
        {% load django_static %}
        {% slimcontent %}
        /* Comment */
        body {
            foo: bar;
        }
        {% endslimcontent %}
        """
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        
        self.assertEqual(rendered, u'body{foo:bar}')
        
        # Now do the same but with some Javascript
        template_as_string = """
        {% load django_static %}
        {% slimcontent %}
        // Comment
        function add(one, two) {
            return one + two;
        }
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        
        self.assertEqual(rendered, u'function add(one,two){return one + two;}')
        
        # Now with some HTML
        template_as_string = """
        {% load django_static %}
        {% slimcontent "xhtml" %}
        <!-- comment! -->
        <html>
            <head>
                <title> TITLE </title>
            </head>
        </html>
        {% endslimcontent %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        
        self.assertEqual(rendered, u'<html><head><title> TITLE </title></head></html>')
        
    def test_slimfiles_scripts(self):
        """test the template tag that is wrapped around multiple
        <script src="..."> tags
        """
        TEST_FILENAME_1 = '/test1.js'
        TEST_FILENAME_2 = '/jscripts/test2.js'

        TEST_SAVE_PREFIX = ''
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME_1, 'w')\
          .write('var a  =  test\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME_1)
        
        os.mkdir(os.path.join(TEST_MEDIA_ROOT, 'jscripts'))
        open(TEST_MEDIA_ROOT + TEST_FILENAME_2, 'w')\
          .write('function sum(arg1, arg2) { return arg1 + arg2; }\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME_2)
        
        if slimmer is None:
            return
        
        template_as_string = """
        {% load django_static %}
        {% slimfiles %}
        <script src="/test1.js"></script>
        <meta name="test" content="junk"/>
        <script 
          language='JavaScript1.2' src='/jscripts/test2.js'"></script>
        {% endslimfiles %}
        """# "'' # a bug in my editor
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        from time import time
        expected_filename = 'test1_test2.%s.js' % int(time())
        expected_tag = '<script type="text/javascript" src="%s"></script>' % \
          expected_filename
        
        self.assertTrue(expected_filename in rendered)
        self.assertTrue("language='JavaScript1.2'" not in rendered)
        self.assertTrue('src="/test1.js"' not in rendered)
        self.assertTrue(expected_filename in os.listdir(TEST_MEDIA_ROOT))

        # the only file left in the media root should be the combined file,
        # the original file and the fake directory
        #print os.listdir(TEST_MEDIA_ROOT)
        self.assertEqual(len(os.listdir(TEST_MEDIA_ROOT)), 3)
        
        
    def test_slimfiles_styles(self):
        """test the template tag that is wrapped around multiple <link href="..."> 
        tags
        """
        
        TEST_FILENAME_1 = '/test1.css'
        TEST_FILENAME_2 = '/css/test2.css'
        TEST_FILENAME_PRINT = '/print.css'

        TEST_SAVE_PREFIX = ''
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = ''
        settings.MEDIA_ROOT = TEST_MEDIA_ROOT
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME_1, 'w')\
          .write('body {\n\tcolor: red;\n}\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME_1)
        
        os.mkdir(os.path.join(TEST_MEDIA_ROOT, 'css'))
        open(TEST_MEDIA_ROOT + TEST_FILENAME_2, 'w')\
          .write('p { color: blue; }\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME_2)
        
        open(TEST_MEDIA_ROOT + TEST_FILENAME_PRINT, 'w')\
          .write('html { margin: 0px; }\n')
        self._notice_file(TEST_MEDIA_ROOT + TEST_FILENAME_PRINT)
        
        if slimmer is None:
            return
        
        template_as_string = """
        {% load django_static %}
        {% slimfiles %}
        <link rel="stylesheet" type="text/css" media="print"
            href="/print.css" />
        <link rel="stylesheet" type="text/css" media="screen"
             href="/test1.css" />
        <meta name="test" content="junk"/>
        <link href='/css/test2.css'
        rel='stylesheet' type='text/css' media='screen'
             />
        {% endslimfiles %}
        """# "'' # a bug in my editor
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        from time import time
        expected_filename = 'test1_test2.%s.css' % int(time())
        expected_tag = '<link rel="stylesheet" type="text/css" media="screen" href="%s"/>' % \
          expected_filename
        
        self.assertTrue(expected_filename in rendered)
        self.assertTrue('href="/print.%s.css"' % int(time()) in rendered)
        self.assertTrue('href="/test1.css"' not in rendered)
        self.assertTrue("href='/css/test2.css'" not in rendered)
        
        # the print file
        expected_filename = 'print.%s.css' % int(time())
        expected_tag = '<link rel="stylesheet" type="text/css" media="print" href="%s"/>' % \
          expected_filename
        self.assertTrue(expected_filename in os.listdir(TEST_MEDIA_ROOT))

        # The files left now should be:
        #  test1.css (original, don't touch)
        #  print.css (original)
        #  print.1257xxxxxx.css (new!)
        #  test1_test2.1257xxxxxx.css (new!)
        #  css (original directory)
        self.assertEqual(len(os.listdir(TEST_MEDIA_ROOT)), 5)
        
    def test_slimfiles_scripts_and_styles(self):
        """test the template tag that is wrapped around multiple <link href="..."> or
        <script src="..."> tags
        """
        pass # WORK HARDER!!!!
        
    def test__combine_filenames(self):
        """test the private function _combine_filenames()"""
        
        filenames = ['/somewhere/else/foo.js',
                     '/somewhere/bar.js',
                     '/somewhere/different/too/foobar.js']
        expect = '/somewhere/foo_bar_foobar.js'
        
        self.assertEqual(_combine_filenames(filenames), expect)
        
        filenames = ['/foo.1243892792.js',
                     '/bar.1243893111.js',
                     '/foobar.js']
        expect = '/foo_bar_foobar.1243893111.js'
        self.assertEqual(_combine_filenames(filenames), expect)
