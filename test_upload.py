import urllib.request
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
body = (
    '--' + boundary + '\r\n'
    'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
    'Content-Type: text/plain\r\n\r\n'
    'Hello world\r\n'
    '--' + boundary + '--\r\n'
)
req = urllib.request.Request(
    'https://meddcl.onrender.com/api/unstructured/upload',
    method='POST',
    data=body.encode(),
    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}
)
try:
    with urllib.request.urlopen(req) as r: 
        print('SUCCESS:', r.read().decode())
except Exception as e:
    print('ERROR:', e)
    if hasattr(e, 'read'): 
        print(e.read().decode())
