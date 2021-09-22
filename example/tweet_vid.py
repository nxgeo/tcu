from requests_oauthlib import OAuth1Session
from tcu import TChunkedUpload, TCUError

CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN = ''
ACCESS_TOKEN_SECRET = ''

cred = (
    CONSUMER_KEY, CONSUMER_SECRET,
    ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)

twt = TChunkedUpload(*cred)
client = OAuth1Session(*cred)

try:
    r = twt.upload_media('your-vid.mp4', 'tweet')
except TCUError as e:
    print(e)
else:
    media_id = r['media_id_string']

    r = client.post('https://api.twitter.com/1.1/statuses/update.json', data={
        'status': 'test TChunkedUpload.',
        'media_ids': [media_id]
    })

    print(r.json())
