from django.shortcuts import render_to_response
from django.template import RequestContext

def page(request):
    return render_to_response('page.html', locals(),
                              context_instance=RequestContext(request))    
