import os
import stat
import sys
import time
import re
from tempfile import mkdtemp, gettempdir
from glob import glob
from base64 import decodestring
from unittest import TestCase
from shutil import rmtree
import warnings

from django_static.templatetags.django_static import _static_file, _combine_filenames
import django_static.templatetags.django_static
def _slim_file(x, symlink_if_possible=False,):
    return _static_file(x, optimize_if_possible=True,
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

#TEST_MEDIA_ROOT = os.path.join(gettempdir(), 'fake_media_root')
#_original_MEDIA_ROOT = settings.MEDIA_ROOT
_original_DEBUG = settings.DEBUG
_original_DJANGO_STATIC_SAVE_PREFIX = getattr(settings, 'DJANGO_STATIC_SAVE_PREFIX', '')
_original_DJANGO_STATIC_NAME_PREFIX = getattr(settings, 'DJANGO_STATIC_NAME_PREFIX', '')
_original_DJANGO_STATIC_MEDIA_URL = getattr(settings, 'DJANGO_STATIC_MEDIA_URL', '')

class TestDjangoStatic(TestCase):
    
    # NOTE! The reason we keep chaning names in the tests is because of the 
    # global object _FILE_MAP in django_static.py (which is questionable)
    
    
    def _notice_file(self, filepath):
        assert os.path.isfile(filepath)
        self.__added_filepaths.append(filepath)
        
    def setUp(self):
        self.__added_filepaths = []
        #if not os.path.isdir(TEST_MEDIA_ROOT):
        #    os.mkdir(TEST_MEDIA_ROOT)
            
        # All tests is going to run off this temp directory
        settings.MEDIA_ROOT = mkdtemp()
        
        # Disable Closure Compiler if set
        settings.DJANGO_STATIC_CLOSURE_COMPILER = None
        
        super(TestDjangoStatic, self).setUp()
        
    def tearDown(self):
        for filepath in self.__added_filepaths:
            if os.path.isfile(filepath):
                os.remove(filepath)
                
        # restore things for other potential tests
        settings.DEBUG = _original_DEBUG
        settings.DJANGO_STATIC_SAVE_PREFIX = _original_DJANGO_STATIC_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = _original_DJANGO_STATIC_NAME_PREFIX
        settings.DJANGO_STATIC_MEDIA_URL = _original_DJANGO_STATIC_MEDIA_URL
        
        assert settings.MEDIA_ROOT.startswith(gettempdir())
        rmtree(settings.MEDIA_ROOT)
        
        super(TestDjangoStatic, self).tearDown()

        
    #####################
    ## Next generation 
    #
    

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

    def test_staticfile_django_static_off(self):
        """You put this in the template:
         {% staticfile "/js/foo.js" %}
        but then you disable DJANGO_STATIC so you should get
          /js/foo.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = False
        
        filename = "/foo.js"
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write('samplecode()\n')
        
        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        template_as_string = """{% load django_static %}
        {% staticfile "/foo.js" %}
        """
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, u"/foo.js")
        
        

    def test_staticfile_single_debug_on(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become 
        /js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        self._test_staticfile_single('/jquery.min.js',
                                     'function () { return 1; }')
        
        
    def test_staticfile_single_debug_off(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become 
        /js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        
        self._test_staticfile_single('/jquery-2.min.js',
                                     'function () { return 1; }')
        
    def test_staticfile_single_debug_off_with_media_url(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become 
        http://static.example.com/js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True        
        settings.DJANGO_STATIC_MEDIA_URL = media_url = 'http://static.example.com'
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')
        
        self._test_staticfile_single('/jquery-3.min.js',
                                     'function () { return 1; }',
                                     media_url=media_url,
                                     name_prefix='/infinity',
                                     save_prefix='special')
        
    def test_staticfile_single_debug_off_with_name_and_save_prefix_with_media_url(self):
        """Most basic test
        {% staticfile "/js/jquery-1.9.9.min.js" %}
        it should become 
        http://static.example.com/js/jquery-1.9.9.min.1257xxxxxx.js
        and unlike slimfile() this file should either be a symlink or
        a copy that hasn't changed.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_MEDIA_URL = media_url = 'http://static.example.com'
        
        self._test_staticfile_single('/jquery-4.min.js',
                                     'function () { return 1; }',
                                     media_url=media_url)        

    def _test_staticfile_single(self, filename, code, name_prefix='', save_prefix='',
                               media_url=''):
        
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write(code + '\n')
        
        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        
        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + filename + '" %}'
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        bits = filename.rsplit('.', 1)
        now = int(time.time())
        new_filename = bits[0] + '.%s.' % now + bits[-1]
        self.assertEqual(rendered, media_url + name_prefix + new_filename)
        
        if save_prefix:
            save_dir = os.path.join(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertTrue(os.path.basename(new_filename) in os.listdir(save_dir))
            # The content of the new file should be the same
            new_file = os.listdir(save_dir)[0]
            new_file_path = os.path.join(save_dir, new_file)
            if sys.platform != "win32":
                self.assertTrue(os.path.islink(new_file_path))
            new_code = open(new_file_path).read()
            self.assertTrue(len(new_code.strip()) == len(code.strip()))
        else:
            media_root_files_after = os.listdir(settings.MEDIA_ROOT)
            # assuming the file isn't in a sub directory
            if len(new_filename.split('/')) <= 2:
                self.assertEqual(len(media_root_files_before) + 1, 
                                 len(media_root_files_after))
                
            # Content shouldn't change    
            new_file = [x for x in media_root_files_after 
                        if x not in media_root_files_before][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)
            if sys.platform != "win32":
                self.assertTrue(os.path.islink(new_file_path))
            new_code = open(new_file_path).read()
            self.assertEqual(len(new_code.strip()), len(code.strip()))
        
        # Run it again just to check that it still works
        rendered = template.render(context).strip()
        self.assertEqual(rendered, media_url + name_prefix + new_filename)
        
        # pretend that time has passed and 10 seconds has lapsed then re-run the
        # rendering again and depending on settings.DEBUG this is noticed
        # or not.
        
        from posix import stat_result
        def fake_stat(arg):
            if arg == test_filepath:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat
        
        rendered = template.render(context).strip()
        if settings.DEBUG:
            new_filename = bits[0] + '.%s.' % (now + 10) + bits[1]
        self.assertEqual(rendered, media_url + name_prefix + new_filename)
        
        if settings.DEBUG:
            
            # when time passes and a new file is created, it's important to test
            # that the previously created one is deleted
            if save_prefix:
                # If you use a save prefix, presumbly the directory where the 
                # timestamped files are saved didn't exist before so we can
                # assume that the file existed before where none
                files_now = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
                self.assertEqual(len(files_now), 1)
            else:
                self.assertEqual(len(media_root_files_before) + 1, 
                                len(os.listdir(settings.MEDIA_ROOT)))
                self.assertNotEqual(sorted(media_root_files_after),
                                    sorted(os.listdir(settings.MEDIA_ROOT)))

    
        
    def test_slimfile_single_debug_on(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        self._test_slimfile_single('/test.js',
                                   'function () { return 1; }')

    def test_slimfile_single_debug_off(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        
        self._test_slimfile_single('/testing.js',
                                   'var a = function() { return ; }')
        
    def test_slimfile_single_debug_off_with_name_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'
        
        self._test_slimfile_single('/testing123.js',
                                   'var a = function() { return ; }',
                                   name_prefix='/infinity')

    def test_slimfile_single_debug_on_with_name_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        self._test_slimfile_single('/testing321.js',
                                   'var a = function() { return ; }',
                                   name_prefix='/infinity')
        
        
    def test_slimfile_single_debug_off_with_save_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')
        
        self._test_slimfile_single('/testingXXX.js',
                                   'var a = function() { return ; }',
                                   save_prefix='special')
        
    def test_slimfile_single_debug_on_with_save_prefix(self):
        """Most basic test
        {% slimfile "/js/foo.js" %}
        it should become:
        /myprefix/js/foo.1257xxxxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'special')
        
        self._test_slimfile_single('/testingAAA.js',
                                   'var a = function() { return ; }',
                                   save_prefix='special')
        

    def _test_slimfile_single(self, filename, code, name_prefix='', save_prefix=''):
        if not slimmer:
            return 
        
        test_filepath = settings.MEDIA_ROOT + filename
        open(test_filepath, 'w').write(code + '\n')
        
        
        media_root_files_before = os.listdir(settings.MEDIA_ROOT)
        
        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + filename + '" %}'
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        bits = filename.split('.')
        now = int(time.time())
        new_filename = bits[0] + '.%s.' % now + bits[1]
        self.assertEqual(rendered, name_prefix + new_filename)
        
        if save_prefix:
            save_dir = os.path.join(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertTrue(os.path.basename(new_filename) in os.listdir(save_dir))
            # The content of the new file should be smaller
            
            new_file = os.path.join(save_dir, os.listdir(save_dir)[0])
            new_code = open(new_file).read()
            self.assertTrue(len(new_code.strip()) < len(code.strip()))
        else:
            media_root_files_after = os.listdir(settings.MEDIA_ROOT)
            # assuming the file isn't in a sub directory
            if len(new_filename.split('/')) <= 2:
                self.assertEqual(len(media_root_files_before) + 1, 
                                 len(media_root_files_after))
                
            # The content of the newly saved file should have been whitespace
            # optimized so we can expect it to contain less bytes
            new_file = [x for x in media_root_files_after 
                        if x not in media_root_files_before][0]
            new_code = open(os.path.join(settings.MEDIA_ROOT, new_file)).read()
            self.assertTrue(len(new_code) < len(code))
        
        # Run it again just to check that it still works
        rendered = template.render(context).strip()
        self.assertEqual(rendered, name_prefix + new_filename)
        
        # pretend that time has passed and 10 seconds has lapsed then re-run the
        # rendering again and depending on settings.DEBUG this is noticed
        # or not.
        
        #time.sleep(1)
        from posix import stat_result
        def fake_stat(arg):
            if arg == test_filepath:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat
        
        rendered = template.render(context).strip()
        if settings.DEBUG:
            new_filename = bits[0] + '.%s.' % (now + 10) + bits[1]
        self.assertEqual(rendered, name_prefix + new_filename)
        
        if settings.DEBUG:
            
            # when time passes and a new file is created, it's important to test
            # that the previously created one is deleted
            if save_prefix:
                # If you use a save prefix, presumbly the directory where the 
                # timestamped files are saved didn't exist before so we can
                # assume that the file existed before where none
                files_now = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
                self.assertEqual(len(files_now), 1)
            else:
                self.assertEqual(len(media_root_files_before) + 1, 
                                len(os.listdir(settings.MEDIA_ROOT)))
                self.assertNotEqual(sorted(media_root_files_after),
                                    sorted(os.listdir(settings.MEDIA_ROOT)))
            
    def test_slimfile_multiple_debug_on(self):
        """Where there are multiple files instead if just one:
        {% slimfile "/js/foo.js; /js/bar.js" %}
        it should become:
        /js/foo_bar.1257xxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        #settings.DJANGO_STATIC_NAME_PREFIX = ''
        
        filenames = ('/test_1.js', '/test_2.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes)
        
    def test_slimfile_multiple_debug_off(self):
        """This is effectively the same as test_slimfile_multiple_debug_on()
        with the exception that this time with DEBUG=False which basically
        means that it assumes that the filename doesn't change if the 
        filename is mapped at all.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        #settings.DJANGO_STATIC_NAME_PREFIX = ''
        
        filenames = ('/test_A.js', '/test_B.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes)
        
    def test_slimfile_multiple_debug_on_with_name_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_X.js', '/test_Y.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, name_prefix='/infinity')
        
    def test_slimfile_multiple_debug_off_with_name_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = False
        settings.DJANGO_STATIC = True
        #settings.DJANGO_STATIC_SAVE_PREFIX = TEST_SAVE_PREFIX
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_P.js', '/test_Q.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, name_prefix='/infinity')
        
    def test_slimfile_multiple_debug_on_with_save_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'forever')

        filenames = ('/test_a.js', '/test_b.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, save_prefix='forever')
        
    def test_slimfile_multiple_debug_on_with_name_and_save_prefix(self):
        """same as test_slimfile_multiple_debug_on() but this time with a
        name prefix.
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        settings.DJANGO_STATIC_SAVE_PREFIX = os.path.join(settings.MEDIA_ROOT, 'forever')
        settings.DJANGO_STATIC_NAME_PREFIX = '/infinity'

        filenames = ('/test_111.js', '/test_222.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimfile_multiple(filenames, codes, 
                                     name_prefix='/infinity',
                                     save_prefix='forever')
        
        
    def _test_slimfile_multiple(self, filenames, codes, name_prefix='', save_prefix=None):
        
        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')
        
        now = int(time.time())

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + '; '.join(filenames) + '" %}'
        # First do it without DJANGO_STATIC_MEDIA_URL set
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        expect_filename = _combine_filenames(filenames)
        bits = expect_filename.split('.')
        expect_filename = expect_filename[:-3]
        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])
        self.assertEqual(rendered, name_prefix + expect_filename)
        
        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            # what we expect in the media root is all the original 
            # filenames plus the newly created one
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))

        rendered = template.render(context).strip()
        
        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% slimfile "' + '; '.join(filenames) + '" as new_src %}\n'
        template_as_string += '{{ new_src }}'
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, name_prefix + expect_filename)
        
        from posix import stat_result
        def fake_stat(arg):
            if arg in test_filepaths:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat
        
        rendered = template.render(context).strip()
        if settings.DEBUG:
            expect_filename = bits[0] + '.%s.' % (now + 10) + bits[-1]
        else:
            # then it shouldn't change.
            # This effectively means that if you have a live server, and you 
            # make some changes to the, say, CSS files your Django templates
            # won't notice this until after you restart Django.
            pass
        
        self.assertEqual(rendered, name_prefix + expect_filename)
        
            
    def test_staticfile_multiple_debug_on(self):
        """Where there are multiple files instead if just one:
        {% slimfile "/js/foo.js; /js/bar.js" %}
        it should become:
        /js/foo_bar.1257xxxxx.js
        """
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/test_33.js', '/test_44.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_staticfile_multiple(filenames, codes)
        
    
    def _test_staticfile_multiple(self, filenames, codes, name_prefix='', 
                                  save_prefix=None):
        
        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')
        
        now = int(time.time())

        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + '; '.join(filenames) + '" %}'
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        expect_filename = _combine_filenames(filenames)
        bits = expect_filename.split('.')
        expect_filename = expect_filename[:-3]
        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])
        self.assertEqual(rendered, name_prefix + expect_filename)
        
        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            # what we expect in the media root is all the original 
            # filenames plus the newly created one
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))
            
            new_file = [x for x in new_filenames_set
                        if x not in filenames_set][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)
            
            # the file shouldn't become a symlink
            if sys.platform != "win32":
                self.assertTrue(os.path.lexists(new_file_path))
                self.assertTrue(not os.path.islink(new_file_path))

        rendered = template.render(context).strip()
        
        template_as_string = '{% load django_static %}\n'
        template_as_string += '{% staticfile "' + '; '.join(filenames) + '" as new_src %}\n'
        template_as_string += '{{ new_src }}'
        
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        self.assertEqual(rendered, name_prefix + expect_filename)
        
        from posix import stat_result
        def fake_stat(arg):
            if arg in test_filepaths:
                faked = list(orig_os_stat(arg))
                faked[stat.ST_MTIME] = faked[stat.ST_MTIME] + 10
                return stat_result(faked)
            else:
                return orig_os_stat(arg)
        orig_os_stat = os.stat
        os.stat = fake_stat
        
        rendered = template.render(context).strip()
        if settings.DEBUG:
            expect_filename = bits[0] + '.%s.' % (now + 10) + bits[-1]
        else:
            # then it shouldn't change.
            # This effectively means that if you have a live server, and you 
            # make some changes to the, say, CSS files your Django templates
            # won't notice this until after you restart Django.
            pass
        
        self.assertEqual(rendered, name_prefix + expect_filename)
        
    def test_staticall_basic(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/test_11.js', '/test_22.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_staticall(filenames, codes)
        
    def test_staticall_one_file_only(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/test_abc.js',)
        codes = ('function (var1, var2)  { return var1+var2; }',)

        self._test_staticall(filenames, codes)
        
    def test_slimall_basic(self):
        if slimmer is None:
            return
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/testxx.js', '/testyy.js')
        codes = ('function (var1, var2)  { return var1+var2; }',
                 'var xxxxx = "yyyy" ;')

        self._test_slimall(filenames, codes)
        
    def test_slimall_basic_css(self):
        if slimmer is None:
            return
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/adam.css', '/eve.css')
        codes = ('body { gender: male; }',
                 'footer { size: small; }')

        self._test_slimall(filenames, codes)

        
    def test_slimall_css_files(self):
        if slimmer is None:
            return
        
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/testxx.css', '/testyy.css')
        codes = ('body { color:blue; }',
                 'p { color:red; }')

        self._test_slimall(filenames, codes,
                           css_medias={'/testxx.css':'screen'})

    def test_slimall_css_files_different_media(self):
        settings.DEBUG = True
        settings.DJANGO_STATIC = True
        
        filenames = ('/screen1.css', '/screen2.css', '/print_this.css')
        codes = ('body { color:blue; }',
                 'p { color:red; }',
                 'body { margin: 0px; }')

        self._test_slimall(filenames, codes,
                           css_medias={'/print_this.css':'print'})        
        
        
    def _test_slimall(self, filenames, codes, name_prefix='', media_url='',
                      save_prefix=None,
                      content_slimmed=True,
                      css_medias=None):
        return self._test_staticall(filenames, codes, name_prefix=name_prefix,
                                    media_url=media_url, save_prefix=save_prefix,
                                    content_slimmed=True,
                                    css_medias=css_medias)

    def _test_staticall(self, filenames, codes, name_prefix='', media_url='',
                        save_prefix=None,
                        content_slimmed=False,
                        css_medias=None):
        
        test_filepaths = []
        for i, filename in enumerate(filenames):
            test_filepath = settings.MEDIA_ROOT + filename
            test_filepaths.append(test_filepath)
            open(test_filepath, 'w')\
              .write(codes[i] + '\n')
        
        now = int(time.time())
        template_as_string = '{% load django_static %}\n'
        if content_slimmed:
            template_as_string += '{% slimall %}\n'
        else:
            template_as_string += '{% staticall %}\n'
            
        for filename in filenames:
            if filename.endswith('.js'):
                template_as_string += '<script src="%s"></script>\n' % filename
            elif filename.endswith('.css'):
                if css_medias and css_medias.get(filename):
                    template_as_string += '<link rel="stylesheet" media="%s" href="%s"/>\n' %\
                      (css_medias.get(filename), filename)
                else:
                    template_as_string += '<link rel="stylesheet" href="%s"/>\n' %\
                      filename
            else:
                raise NotImplementedError('????')
            
        if content_slimmed:
            template_as_string += '{% endslimall %}'
        else:
            template_as_string += '{% endstaticall %}'
            
        if filenames[0].endswith('.js'):
            assert template_as_string.count('<script ') == len(filenames)
        elif filenames[0].endswith('.css'):
            assert template_as_string.count('<link ') == len(filenames)
            
        template = Template(template_as_string)
        context = Context()
        rendered = template.render(context).strip()
        if filenames[0].endswith('.js'):
            self.assertEqual(rendered.count('<script '), 1)
        elif filenames[0].endswith('.css'):
            if css_medias is None:
                distinct_medias = set()
            else:
                distinct_medias = set(css_medias.values())
            if 'screen' not in distinct_medias:
                distinct_medias.add('screen')
            minimum = len(distinct_medias)
            self.assertEqual(rendered.count('<link '), minimum, 
                             rendered.count('<link '))
            
        expect_filename = _combine_filenames(filenames)
        bits = expect_filename.split('.')
        if filenames[0].endswith('.js'):
            expect_filename = expect_filename[:-3]
        elif filenames[0].endswith('.css'):
            if len(distinct_medias) > 1:
                # this is too complicated to test at the moment
                return
            expect_filename = expect_filename[:-4]

        expect_filename += '.%s%s' % (now, os.path.splitext(filenames[0])[1])
        
        self.assertTrue(expect_filename in rendered, expect_filename)
        
        # this should have created a new file
        if save_prefix:
            new_filenames_set = os.listdir(os.path.join(settings.MEDIA_ROOT, save_prefix))
            self.assertEqual(len(new_filenames_set), 1)
        else:
            filenames_set = set(os.path.basename(x) for x in filenames)
            new_filenames_set = set(os.listdir(settings.MEDIA_ROOT))
            self.assertEqual(new_filenames_set & filenames_set, filenames_set)
            self.assertEqual(len(filenames_set) + 1, len(new_filenames_set))
            
            new_file = [x for x in new_filenames_set
                        if x not in filenames_set][0]
            new_file_path = os.path.join(settings.MEDIA_ROOT, new_file)
            
            filepaths = [os.path.join(settings.MEDIA_ROOT, x) for x in filenames_set]
            
            # the file shouldn't become a symlink
            if sys.platform != "win32" and len(filenames) > 1:
                # unless it's just a single file
                self.assertTrue(os.path.lexists(new_file_path))
                self.assertTrue(not os.path.islink(new_file_path))
                
                # the content should be the codes combined
                content = open(new_file_path).read()
                expect_content = '\n'.join(codes)
                if content_slimmed:
                    self.assertTrue(len(content.strip()) < len(expect_content.strip()))
                else:
                    self.assertEqual(content.strip(), expect_content.strip())
        
