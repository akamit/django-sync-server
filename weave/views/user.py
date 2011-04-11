# coding:utf-8

'''
    User handling for Weave.
    FIXME: Not complete yet.
    
    Created on 15.03.2010
    
    @license: GNU GPL v3 or above, see LICENSE for more details.
    @copyleft: 2010-2011 by the django-sync-server team, see AUTHORS for more details.
'''
try:
    import json # New in Python v2.6
except ImportError:
    from django.utils import simplejson as json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponse, \
    HttpResponseNotFound

# django-sync-server own stuff
from weave import constants
from weave.decorators import logged_in_or_basicauth, weave_assert_version
from weave import Logging

logger = Logging.get_logger()

@weave_assert_version('1.0')
@logged_in_or_basicauth
@csrf_exempt
def password(request):
    """
    Change the user password.
    """
    if request.method != 'POST':
        logger.error("wrong request method %r" % request.method)
        return HttpResponseBadRequest()

    # Make sure that we are able to change the password. 
    # If for example django-auth-ldap is used for authentication it will set the password for 
    # User objects to a unusable one in the database. Therefore we cannot change it, it has to 
    # happen inside LDAP.
    if not request.user.has_usable_password():
        logger.debug("Can't change password. User %s has a unusable password." % request.user.username)
        return HttpResponseBadRequest()

    # The PHP server for Weave uses the first 2048 (if there is enough data) characters
    # from POST data as the new password. We decided to throw an error if the password 
    # data is longer than 256 characters.
    if len(request.raw_post_data) > 256:
        msg = (
            "Don't change password for user %s."
            " POST data has more than 256 characters! (len=%i)"
        ) % (request.user.username, len(request.raw_post_data))
        logger.debug(msg)
        return HttpResponseBadRequest()

    request.user.set_password(request.raw_post_data)
    request.user.save()
    logger.debug("Password for User %r changed to %r" % (request.user.username, request.raw_post_data))
    return HttpResponse()


@weave_assert_version('1.0')
@csrf_exempt
def node(request, version, username):
    """
    finding cluster for user -> return 404 -> Using serverURL as data cluster (multi-cluster support disabled)
    """

    try:
        User.objects.get(username=username)
    except User.DoesNotExist:
        logger.debug("User %r doesn't exist!" % username)
        return HttpResponseNotFound(constants.ERR_UID_OR_EMAIL_AVAILABLE)
    else:
        logger.debug("User %r exist." % username)
        #FIXME: Send the actual cluster URL instead of 404
        return HttpResponseNotFound(constants.ERR_UID_OR_EMAIL_IN_USE)


@csrf_exempt
def register_check(request, username):
    """
    returns "1" if username is available (doesn't exist)
    https://wiki.mozilla.org/Labs/Weave/ServerAPI#Checking_if_Username.2FEmail_already_exists
    """
    try:
        User.objects.get(username=username)
    except User.DoesNotExist:
        logger.debug("User %r doesn't exist!" % username)
        return HttpResponse(constants.ERR_UID_OR_EMAIL_AVAILABLE)
    else:
        logger.debug("User %r exist." % username)
        return HttpResponse(constants.ERR_UID_OR_EMAIL_IN_USE)

@weave_assert_version('1.0')
@csrf_exempt
def exists(request, version, username):
    """
    https://wiki.mozilla.org/Labs/Weave/User/1.0/API#GET
    Returns 1 if the username is in use, 0 if it is available.
    
    e.g.: https://auth.services.mozilla.com/user/1/UserName
    """
    if request.method == 'GET':
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            logger.debug("User %r doesn't exist!" % username)
            return HttpResponse(constants.USER_DOES_NOT_EXIST)
        else:
            logger.debug("User %r exist." % username)
            return HttpResponse(constants.USER_EXIST)
    elif request.method == 'PUT':
        # Check for aviability of recaptcha 
        # (can be found at: http://pypi.python.org/pypi/recaptcha-client)
        try:
            from recaptcha.client.captcha import submit
        except ImportError:
            logger.error("Captcha requested but unable to import the 'recaptcha' package!")
            return HttpResponse("Captcha support disabled due to missing Python package 'recaptcha'.")
        if not getattr(settings.WEAVE, "RECAPTCHA_PRIVATE_KEY"):
            logger.error("Trying to create user but settings.WEAVE.RECAPTCHA_PRIVATE_KEY not set")
            raise ImproperlyConfigured
        # Handle user creation.
        data = json.loads(request.raw_post_data)
        # Usernames are limited to a length of max. 30 chars.
        # http://docs.djangoproject.com/en/dev/topics/auth/#django.contrib.auth.models.User.username
        if len(username) > 30 or len(data['password']) > 256:
            return HttpResponseBadRequest()
        result = submit(
                        data['captcha-challenge'],
                        data['captcha-response'],
                        settings.WEAVE.RECAPTCHA_PRIVATE_KEY,
                        request.META['REMOTE_ADDR']
                        )
        if not result.is_valid:
            # Captcha failed.
            return HttpResponseBadRequest()
        User.objects.create_user(username, data['email'], data['password'])
        return HttpResponse()
    else:
        raise NotImplemented()
