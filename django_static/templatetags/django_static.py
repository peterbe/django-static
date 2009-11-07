# python
import os
import re
import sys
import stat
from glob import glob
from collections import defaultdict

try:
    from slimmer import css_slimmer, guessSyntax, html_slimmer, js_slimmer, xhtml_slimmer
    slimmer = 'installed'
except ImportError:
    slimmer = None
    import warnings
    warnings.warn("slimmer is not installed. (easy_install slimmer)")

from pprint import pprint

if sys.platform == "win32":
    _CAN_SYMLINK = False
else:
    _CAN_SYMLINK = True
    import subprocess
    
def _symlink(from_, to):
    cmd = 'ln -s "%s" "%s"' % (from_, to)
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    

# django 
from django import template
from django.conf import settings

register = template.Library()

## These two methods are put here if someone wants to access the django_static
## functionality from code rather than from a django template
## E.g.
##   from django_static import slimfile
##   print slimfile('/css/foo.js')

def slimfile(filename):
    return _static_file(filename,
                        symlink_if_possible=_CAN_SYMLINK,
                        slimmer_if_possible=True)

def staticfile(filename):
    return _static_file(filename,
                        symlink_if_possible=_CAN_SYMLINK,
                        slimmer_if_possible=False)





class SlimContentNode(template.Node):
    
    def __init__(self, nodelist, format=None):
        self.nodelist = nodelist
        self.format = format
        
    def render(self, context):
        code = self.nodelist.render(context)
        if slimmer is None:
            return code
        
        if self.format not in ('css','js','html','xhtml'):
            self.format = guessSyntax(code)
            
        if self.format == 'css':
            return css_slimmer(code)
        elif self.format in ('js', 'javascript'):
            return js_slimmer(code)
        elif self.format == 'xhtml':
            return xhtml_slimmer(code)
        elif self.format == 'html':
            return html_slimmer(code)
            
        return code

    

@register.tag(name='slimcontent')
def do_slimcontent(parser, token):
    nodelist = parser.parse(('endslimcontent',))
    parser.delete_first_token()
    
    _split = token.split_contents()
    format = ''
    if len(_split) > 1:
        tag_name, format = _split
        if not (format[0] == format[-1] and format[0] in ('"', "'")):
            raise template.TemplateSyntaxError, \
                          "%r tag's argument should be in quotes" % tag_name
                          
    return SlimContentNode(nodelist, format[1:-1])



    
    


@register.tag(name='slimfile')
def slimfile_node(parser, token):
    _split = token.split_contents()
    tag_name = _split[0]
    options = _split[1:]
    try:
        filename = options[0]
        if not (filename[0] == filename[-1] and filename[0] in ('"', "'")):
            raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name
        filename = filename[1:-1]
    except IndexError:
        raise template.TemplateSyntaxError("Filename not specified")
    
    return StaticFileNode(filename,
                          symlink_if_possible=_CAN_SYMLINK,
                          slimmer_if_possible=True)

@register.tag(name='staticfile')
def staticfile_node(parser, token):
    _split = token.split_contents()
    tag_name = _split[0]
    options = _split[1:]
    try:
        filename = options[0]
        if not (filename[0] == filename[-1] and filename[0] in ('"', "'")):
            raise template.TemplateSyntaxError, "%r tag's argument should be in quotes" % tag_name
        filename = filename[1:-1]
    except IndexError:
        raise template.TemplateSyntaxError("Filename not specified")
    
    return StaticFileNode(filename, symlink_if_possible=_CAN_SYMLINK)

class StaticFileNode(template.Node):
    
    def __init__(self, filename, slimmer_if_possible=False, 
                 symlink_if_possible=False):
        self.filename = filename
        self.slimmer_if_possible = slimmer_if_possible
        self.symlink_if_possible = symlink_if_possible
        
    def render(self, context):
        return _static_file(self.filename,
                            slimmer_if_possible=self.slimmer_if_possible,
                            symlink_if_possible=self.symlink_if_possible)



class StaticFilesNode(template.Node):
    """find all static files in the wrapped code and run staticfile (or 
    slimfile) on them all by analyzing the code.
    """
    def __init__(self, nodelist, slimmer_if_possible=False,
                 symlink_if_possible=False):
        self.nodelist = nodelist
        self.slimmer_if_possible = slimmer_if_possible
        
        self.symlink_if_possible = symlink_if_possible
        
    def render(self, context):
        code = self.nodelist.render(context)
        js_files = []
        scripts_regex = re.compile('<script [^>]*src=["\']([^"\']+)["\'].*?</script>')
        styles_regex = re.compile('<link.*?href=["\']([^"\']+)["\'].*?>', re.M|re.DOTALL)
        
        new_js_filenames = []
        for match in scripts_regex.finditer(code):
            whole_tag = match.group()
            for filename in match.groups():
                
                slimmer_if_possible = self.slimmer_if_possible
                if slimmer_if_possible and filename.endswith('.min.js'):
                    # Override! Because we simply don't want to run slimmer
                    # on files that have the file extension .min.js
                    slimmer_if_possible = False
                    
                    
                new_filename = _static_file(filename, 
                                            slimmer_if_possible=slimmer_if_possible,
                                            symlink_if_possible=self.symlink_if_possible)
                if new_filename != filename:
                    # it worked!
                    new_js_filenames.append(new_filename)
                    
                    code = code.replace(whole_tag, '')
                    
        # Now, we need to combine these files into one
        if new_js_filenames:
            new_js_filename = _combine_filenames(new_js_filenames)
        else:
            new_js_filename = None
            
            
        new_css_filenames = defaultdict(list)
        
        # It's less trivial with CSS because we can't combine those that are
        # of different media
        media_regex = re.compile('media=["\']([^"\']+)["\']')
        for match in styles_regex.finditer(code):
            whole_tag = match.group()
            #print "WHOLE_TAG", repr(whole_tag)
            try:
                media_type = media_regex.findall(whole_tag)[0]
            except IndexError:
                # Because it's so common
                media_type = 'screen'
                
            for filename in match.groups():
                new_filename = _static_file(filename, 
                                            slimmer_if_possible=self.slimmer_if_possible,
                                            symlink_if_possible=self.symlink_if_possible)
                
                if new_filename != filename:
                    # it worked!
                    new_css_filenames[media_type].append(new_filename)
                    
                    code = code.replace(whole_tag, '')
                
        # Now, we need to combine these files into one
        new_css_filenames_combined = {}
        if new_css_filenames:
            for media_type, filenames in new_css_filenames.items():
                new_css_filenames_combined[media_type] = _combine_filenames(filenames)
        
        # When we make up this new file we have to understand where to write it
        try:
            DJANGO_STATIC_SAVE_PREFIX = settings.DJANGO_STATIC_SAVE_PREFIX
        except AttributeError:
            DJANGO_STATIC_SAVE_PREFIX = ''
        PREFIX = DJANGO_STATIC_SAVE_PREFIX and DJANGO_STATIC_SAVE_PREFIX or \
          settings.MEDIA_ROOT
        
        if new_js_filename:
            new_js_filepath = _filename2filepath(new_js_filename, PREFIX)
        #    for old_filepath in glob(re.sub('\.\d{10}.', '.*.', new_js_filepath)):
        #        os.remove(old_filepath)
            

        # If there was a file with the same name there already but with a different
        # timestamp, then delete it
        
        if new_js_filenames:
            new_file = open(new_js_filepath, 'w')
            for filename in new_js_filenames:
                old_filepath = _filename2filepath(filename, PREFIX)
                new_file.write("%s\n" % open(old_filepath).read())
                os.remove(old_filepath)
            new_file.close()
            
        if new_js_filename:
            new_tag = '<script type="text/javascript" src="%s"></script>' % \
              new_js_filename
            code = "%s%s" % (new_tag, code)
        
        for media_type, new_css_filename in new_css_filenames_combined.items():
            new_css_filepath = _filename2filepath(new_css_filename, PREFIX)
            
            new_file = open(new_css_filepath, 'w')
            redundant_filenames = new_css_filenames[media_type]
            
            for filename in redundant_filenames:
                old_filepath = _filename2filepath(filename, PREFIX)
                new_file.write("%s\n" % open(old_filepath).read())
                # The old file should only be removed if multiple files were
                # actually combined into one
                if len(redundant_filenames) > 1:
                    #print "** REMOVE", old_filepath
                    os.remove(old_filepath)
            new_file.close()
            
            new_tag = '<link rel="stylesheet" type="text/css" media="%s" href="%s"/>' % \
              (media_type, new_css_filename)
            
            code = "%s%s" % (new_tag, code)
        
        return code
            
        
                 
                 
@register.tag(name='slimfiles')
def do_slimfiles(parser, token):
    nodelist = parser.parse(('endslimfiles',))
    parser.delete_first_token()
    
    return StaticFilesNode(nodelist,
                           symlink_if_possible=_CAN_SYMLINK,
                           slimmer_if_possible=True)


@register.tag(name='staticfiles')
def do_staticfiles(parser, token):
    nodelist = parser.parse(('endstaticfiles',))
    parser.delete_first_token()
    
    return StaticFilesNode(nodelist,
                           symlink_if_possible=_CAN_SYMLINK,
                           slimmer_if_possible=False)


    
_FILE_MAP = {}

referred_css_images_regex = re.compile('url\(([^\)]+)\)')

def _static_file(filename, 
                 slimmer_if_possible=False,
                 symlink_if_possible=False,
                 warn_no_file=True):
    from time import time
    t0=time()
    r = _static_file_timed(filename, slimmer_if_possible=slimmer_if_possible,
                           symlink_if_possible=symlink_if_possible,
                           warn_no_file=warn_no_file)
    t1=time()
    #print (t1-t0), filename
    return r
        
        
def _static_file_timed(filename,
                       slimmer_if_possible=False, 
                       symlink_if_possible=False,
                       warn_no_file=True):

    
    try:
        DJANGO_STATIC = settings.DJANGO_STATIC
        if not DJANGO_STATIC:
            return filename
    except AttributeError:
        return filename
    
    try:
        DJANGO_STATIC_SAVE_PREFIX = settings.DJANGO_STATIC_SAVE_PREFIX
    except AttributeError:
        DJANGO_STATIC_SAVE_PREFIX = ''
        
    try:
        DJANGO_STATIC_NAME_PREFIX = settings.DJANGO_STATIC_NAME_PREFIX
    except AttributeError:
        DJANGO_STATIC_NAME_PREFIX = ''

    DEBUG = settings.DEBUG
    PREFIX = DJANGO_STATIC_SAVE_PREFIX and DJANGO_STATIC_SAVE_PREFIX or \
      settings.MEDIA_ROOT
    
    try:
        MEDIA_URL = settings.DJANGO_STATIC_MEDIA_URL
    except AttributeError:
        MEDIA_URL = None
    
    def wrap_up(filename):
        if MEDIA_URL:
            return MEDIA_URL + filename
        return filename
        
    new_filename, m_time = _FILE_MAP.get(filename, (None, None))
    
    # we might already have done a conversion but the question is
    # if the javascript or css file has changed. This we only want
    # to bother with when in DEBUG mode because it adds one more 
    # unnecessary operation.
    if new_filename:
        if DEBUG:
            # need to check if the original has changed
            old_new_filename = new_filename
            new_filename = None
        else:
            # This is really fast and only happens when NOT in DEBUG mode
            # since it doesn't do any comparison 
            return wrap_up(new_filename)
    else:
        # This is important so that we can know that there wasn't an 
        # old file which will help us know we don't need to delete 
        # the old one
        old_new_filename = None
        
    if not new_filename:
        filepath = _filename2filepath(filename, settings.MEDIA_ROOT)
        if not os.path.isfile(filepath):
            if warn_no_file:
                import warnings; warnings.warn("Can't find file %s" % filepath)
            return wrap_up(filename)
        
        new_m_time = os.stat(filepath)[stat.ST_MTIME]
        if m_time:
            # we had the filename in the map
            if m_time != new_m_time:
                # ...but it has changed!
                m_time = None
            else:
                # ...and it hasn't changed!
                return wrap_up(old_new_filename)
            
        if not m_time:
            # We did not have the filename in the map OR it has changed
            apart = os.path.splitext(filename)
            new_filename = ''.join([apart[0], 
                                '.%s' % new_m_time,
                                apart[1]])
            
            #new_filename = DJANGO_STATIC_NAME_PREFIX + new_filename
            
            _FILE_MAP[filename] = (DJANGO_STATIC_NAME_PREFIX + new_filename, new_m_time)
            if old_new_filename:
                os.remove(_filename2filepath(old_new_filename.replace(DJANGO_STATIC_NAME_PREFIX, ''),
                                             PREFIX))

    new_filepath = _filename2filepath(new_filename, PREFIX)
     
    # Files are either slimmered or symlinked or just copied. Basically, only
    # .css and .js can be slimmered but not all are. For example, an already
    # minified say jquery.min.js doesn't need to be slimmered nor does it need
    # to be copied. 
    # If you're on windows, it will always have to do a copy. 
    # When symlinking, what the achievement is is that it gives the file a 
    # unique and different name than the original. 
    #
    # The caller of this method is responsible for dictacting if we're should
    # slimmer and if we can symlink.
    
    if slimmer_if_possible:
        # Then we expect to be able to modify the content and we will 
        # definitely need to write a new file. 
        content = open(filepath).read()
        if new_filename.endswith('.js') and slimmer is not None:
            content = js_slimmer(content)
        elif new_filename.endswith('.css') and slimmer is not None:
            content = css_slimmer(content)
            # and _static_file() all images refered in the CSS file itself
            def replacer(match):
                filename = match.groups()[0]
                if (filename.startswith('"') and filename.endswith('"')) or \
                  (filename.startswith("'") and filename.endswith("'")):
                    filename = filename[1:-1]
                # It's really quite common that the CSS file refers to the file 
                # that doesn't exist because if you refer to an image in CSS for
                # a selector you never use you simply don't suffer.
                # That's why we say not to warn on nonexisting files
                new_filename = _static_file(filename, symlink_if_possible=symlink_if_possible,
                                            warn_no_file=DEBUG and True or False)
                return match.group().replace(filename, new_filename)
            content = referred_css_images_regex.sub(replacer, content)
        elif slimmer:
            raise ValueError(
              "Unable to slimmer file %s. Unrecognized extension" % new_filename)
        #print "** STORING:", new_filepath
        open(new_filepath, 'w').write(content)
    elif symlink_if_possible:
        _symlink(filepath, new_filepath)
    else:
        #print "** STORING:", new_filepath
        open(new_filepath, 'w').write(content)
                            
    return wrap_up(DJANGO_STATIC_NAME_PREFIX + new_filename)


def _mkdir(newdir):
    """works the way a good mkdir should :)
        - already exists, silently complete
        - regular file in the way, raise an exception
        - parent directory(ies) does not exist, make them as well
    """
    if os.path.isdir(newdir):
        pass
    elif os.path.isfile(newdir):
        raise OSError("a file with the same name as the desired " \
                      "dir, '%s', already exists." % newdir)
    else:
        head, tail = os.path.split(newdir)
        if head and not os.path.isdir(head):
            _mkdir(head)
        if tail:
            os.mkdir(newdir)
            
            
def _filename2filepath(filename, media_root):
    # The reason we're doing this is because the templates will 
    # look something like this:
    # src="{{ MEDIA_URL }}/css/foo.css"
    # and if (and often happens in dev mode) MEDIA_URL will 
    # just be ''
    
    if filename.startswith('/'):
        path = os.path.join(media_root, filename[1:])
    else:
        path = os.path.join(media_root, filename)
        
    if not os.path.isdir(os.path.dirname(path)):
        _mkdir(os.path.dirname(path))
        
    return path
    
    
    
def _combine_filenames(filenames):
    """Return a new filename to use as the combined file name for a 
    bunch files. 
    A precondition is that they all have the same file extension
    
    Given that the list of files can have different paths, we aim to use the 
    most common path.
    
    Example:
      /somewhere/else/foo.js
      /somewhere/bar.js
      /somewhere/different/too/foobar.js
    The result will be
      /somewhere/foo_bar_foobar.js
      
    Another thing to note, if the filenames have timestamps in them, combine
    them all and use the highest timestamp.
    
    """
    path = None
    names = []
    extension = None
    timestamps = []
    for filename in filenames:
        name = os.path.basename(filename)
        if not extension:
            extension = os.path.splitext(name)[1]
        elif os.path.splitext(name)[1] != extension:
            raise ValueError("Can't combine multiple file extensions")
        
        for each in re.finditer('\.\d{10}\.', name):
            timestamps.append(int(each.group().replace('.','')))
            name = name.replace(each.group(), '.')
        name = os.path.splitext(name)[0]
        names.append(name)
        
        if path is None:
            path = os.path.dirname(filename)
        else:
            if len(os.path.dirname(filename)) < len(path):
                path = os.path.dirname(filename)
    
    
    new_filename = '_'.join(names)
    if timestamps:
        new_filename += ".%s" % max(timestamps)
    
    new_filename += extension
    
    return os.path.join(path, new_filename)
                