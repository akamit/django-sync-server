# coding:utf-8

'''
Created on 27.03.2010

    @license: GNU GPL v3 or above, see LICENSE for more details.
    @copyleft: 2010 by the django-weave team, see AUTHORS for more details.
'''
# Due to Mozilla Weave supporting Recaptcha solely, we have to stick with it until
# they decide to change the interface to pluggable captchas.
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.csrf.middleware import csrf_exempt
from django.http import HttpResponse

# django-weave own stuff
from weave import Logging
from weave.decorators import weave_assert_version

logger = Logging.get_logger()

@weave_assert_version('1.0')
@csrf_exempt
def captcha(request, version):
    # Check for aviability of recaptcha 
    # (can be found at: http://pypi.python.org/pypi/recaptcha-client)
    try:
        from recaptcha.client.captcha import displayhtml
    except ImportError:
        logger.error("Captcha requested but unable to import the 'recaptcha' package!")
        return HttpResponse("Captcha support disabled due to missing Python package 'recaptcha'.")
    if not getattr(settings.WEAVE, "RECAPTCHA_PUBLIC_KEY"):
        logger.error("Trying to create user but settings.WEAVE.RECAPTCHA_PUBLIC_KEY not set")
        raise ImproperlyConfigured
    # Send a simple HTML to the client. It get's rendered inside the Weave client.
    return HttpResponse("<html><body>%s</body></html>" % displayhtml(settings.WEAVE.RECAPTCHA_PUBLIC_KEY))
