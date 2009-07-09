# python
import os
import re
import sys
import stat

try:
    from slimmer import css_slimmer, guessSyntax, html_slimmer, js_slimmer
except ImportError:
    raise ImportError("slimmer not installed! Go do an easy_install slimmer")

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

class SlimContentNode(template.Node):
    def __init__(self, nodelist, format=None):
        self.nodelist = nodelist
        self.format = format
    def render(self, context):
        code = self.nodelist.render(context)
        if self.format == 'css':
            return css_slimmer(code)
        elif self.format in ('js', 'javascript'):
            return js_slimmer(code)
        elif self.format == 'html':
            return html_slimmer(code)
        else:
            format = guessSyntax(code)
            if format:
                self.format = format
                return self.render(context)
            
        return code

    
register = template.Library()
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
    PREFIX = DJANGO_STATIC_SAVE_PREFIX and DJANGO_STATIC_SAVE_PREFIX or settings.MEDIA_ROOT

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
            return new_filename
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
            return filename
        
        new_m_time = os.stat(filepath)[stat.ST_MTIME]
        if m_time:
            # we had the filename in the map
            if m_time != new_m_time:
                # ...but it has changed!
                m_time = None
            else:
                # ...and it hasn't changed!
                return old_new_filename
            
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
        if new_filename.endswith('.js'):
            content = js_slimmer(content)
        elif new_filename.endswith('.css'):
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
        else:
            raise ValueError(
              "Unable to slimmer file %s. Unrecognized extension" % new_filename)
        #print "** STORING:", new_filepath
        open(new_filepath, 'w').write(content)
    elif symlink_if_possible:
        _symlink(filepath, new_filepath)
    else:
        #print "** STORING:", new_filepath
        open(new_filepath, 'w').write(content)
                            
    return DJANGO_STATIC_NAME_PREFIX + new_filename


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
    
    