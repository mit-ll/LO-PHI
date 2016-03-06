import urllib2
import httplib

#url = 'http://localhost:13400/boot?mac=BC-30-5B-BD-5E-B9&uuid=44454C4C-4C00-1058-8058-B4C04F505131'
url = 'http://172.25.57.83:13400/boot?mac=BC-30-5B-BD-5E-B9&uuid=44454C4C-4C00-1058-8058-B4C04F505131'

proxy_handler = urllib2.ProxyHandler({})
opener = urllib2.build_opener(proxy_handler)
page = opener.open(url)

# try:
#     up = urllib2.urlopen(url, timeout=5)
#     for l in up:
#         try:
#             # Look for extra definition within the reply
#             k, v = [x.strip() for x in l.split(':')]
#             k = k.lower()
#             if k == 'client':
#                 hostname = v
#                 if k == 'file':
#                     filename = v
#         except ValueError:
#             pass
# except urllib2.HTTPError, e:
#     print 'HTTP Error: %s' % str(e)
# except urllib2.URLError, e:
#     print 'Internal error: %s' % str(e)
# except httplib.HTTPException, e:
#     print 'Server error: %s' % type(e)
