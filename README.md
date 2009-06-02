About django-static
===================

What it does
------------

`django_static` is a Django app that enables as various template tags
for better serving your static content. It basically rewrites
references to static files and where applicable it does whitespace
optmization of the content. By making references to static content
unique (timestamp included in the name) you can be very aggressive
with your cache-control settings without ever having to worry about
upgrading your code and worrying about visitors using an older version.

The three template tags it enables are the following:

1. `staticfile` Takes the timestamp of the file, and makes a copy by
   symlinking as you define. You use it like this::
   
        <img src="{% staticfile "/images/foo.png" %}"/>
	
   and the following is rendered:
   
        <img src="/images/foo.123456789.png"/>
	
   ...assuming the epoch timestamp of the file is 123456789. 
   
2. `slimfile` Works the same as `staticfile` but instead of copying
   the file as a symlink it actually rewrites the file and compresses
   it through [slimmer](http://pypi.python.org/pypi/slimmer/). This of
   course only works for `.js` and `.css` files but it works
   wonderfully fast and is careful enough to not break things. The
   cool thing about doing this for `.css` files it finds all relative
   images inside and applies `staticfile` for all of them too. You use
   it just like `staticfile`:
   
        <script type="text/javascript"
          src="{% slimfile "/javascript/myscript.js" %}"></script>
	  
3. `slimcontent` is used to whitespace compress content right in the
   template. It requires a format paramter which can be `"js"`,
   `"css"` or `"html"`. So, for example for some inline CSS content
   you do this:
   
        <style type="text/css">
        {% slimcontent "css" %}
        h1, h2, h3 { 
	    font-face:'Trebuchet MS', Verdana, Arial; 
	}
        {% endslimcontent %}
        </style>
	
   ...and you get this:
   
        <style type="text/css">
        h1,h2,h3{font-face:'Trebuchet MS',Verdana,Arial}
        </style>
	
	
Configuration
-------------

`django_static` will be disabled by default. It's not until you set
`DJANGO_STATIC = True` in your settings module that it actually starts
to work for you. 

By default, when `django_static` slims files or makes symlinks with
timestamps in the filename, it does this into the same directory as
where the original file is. If you don't like that you can override
the save location by setting
`DJANGO_STATIC_SAVE_PREFIX=/tmp/django-static`

If you, for the sake of setting up your nginx/varnish/apache2, want
change the name the files get you can set
`DJANGO_STATIC_NAME_PREFIX=/cache-forever` as this will make it easier
to write a rewrite rule/regular expression that in
nginx/varnish/apache2 deliberately sets extra aggressive caching. 

	
How to hook this up with nginx
------------------------------

xxx


	       
	
   
   