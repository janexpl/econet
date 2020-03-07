import requests
from datetime import datetime
import time
r = requests.get('https://www.econet24.com')
payload = {'username': 'janexpl@me.com', 'password': 'Sloneczna#2013',
           'csrfmiddlewaretoken': r.cookies['csrftoken']}
url = "https://www.econet24.com/login/?next=main/"
rx = requests.post(url, data=payload)
csrftoken = rx.history[0].cookies['csrftoken']
sessionId = rx.history[0].cookies['sessionid']
for cookie in rx.history[0].cookies:
    if cookie.name == 'csrftoken':
        expiry = cookie.expires

print(csrftoken + " " + sessionId + " " + str(expiry) + " " + str(time.time()))

print(str(expiry - time.time()))
