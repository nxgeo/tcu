from requests import post
from tcu import OAuth1, TChunkedUpload, TCUError

CONSUMER_KEY = ''
CONSUMER_SECRET = ''
ACCESS_TOKEN = ''
ACCESS_TOKEN_SECRET = ''

auth = OAuth1(
    CONSUMER_KEY, CONSUMER_SECRET,
    ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)

twt = TChunkedUpload(auth)

try:
    r = twt.upload_media('your-vid.mp4', 'TweetVideo')
except TCUError as e:
    print(e)
else:
    data = {
        'status': 'test TChunkedUpload.',
        'media_ids': [r['media_id_string']]
    }

    r = post('https://api.twitter.com/1.1/statuses/update.json',
             data, auth=auth)

    print(r.json())
