"""HTTPS recovery requests with a fail-closed, per-hop origin/path policy."""

import urllib.parse
import urllib.request


def validate_url(url, scope):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.username or parsed.password
            or parsed.port not in (None, 443) or '\\' in url):
        raise ValueError('Recovery requires an HTTPS URL without credentials')
    path = urllib.parse.unquote(parsed.path)
    if '\\' in path or any(ord(c) < 32 for c in path) or any(part in ('.', '..') for part in path.split('/')):
        raise ValueError('Recovery URL contains traversal segments')
    if scope == 'wayback':
        allowed = parsed.hostname == 'web.archive.org' and path.startswith(('/web/', '/cdx/'))
    else:
        allowed = parsed.hostname in ('pcssalumni.com', 'www.pcssalumni.com')
        allowed = allowed and path.startswith(('/wp-json/wp/v2/', '/wp-content/uploads/') if scope == 'wordpress' else ('/PDF/',))
    if not allowed:
        raise ValueError(f'Recovery destination outside {scope} allowlist')
    return url


class RestrictedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, scope):
        self.scope = scope

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.scope)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_recovery(request, *, scope, timeout):
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    validate_url(url, scope)
    return urllib.request.build_opener(RestrictedRedirect(scope)).open(request, timeout=timeout)
