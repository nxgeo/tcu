from mimetypes import guess_type
from os.path import abspath, getsize, splitext
from time import sleep
from typing import Iterator

from requests import Session
from requests_oauthlib import OAuth1


class TCUError(Exception):
    pass


class TChunkedUpload:
    """
    Upload media using chunked POST media/upload endpoints.

    Reference:
    https://developer.twitter.com/en/docs/twitter-api/v1/media/upload-media/uploading-media/chunked-media-upload
    """
    RESOURCE_URL = 'https://upload.twitter.com/1.1/media/upload.json'

    def __init__(self, auth: OAuth1) -> None:
        self.auth = auth
        self.file = None
        self.media_category = None
        self.media_id = None

    def _request(self, method, data=None, params=None, files=None):
        with Session() as s:
            response = s.request(
                method, TChunkedUpload.RESOURCE_URL, params, data,
                files=files, auth=self.auth
            )

        if not response.ok:
            raise TCUError(response.json()['errors'])

        if response.status_code == 204:
            return True

        return response.json()

    def _init(self, additional_owners: list = None) -> dict:
        """Initiate a file upload session."""
        r = self._request('POST', {
            'command': 'INIT',
            'total_bytes': getsize(self.file),
            'media_type': guess_type(self.file)[0],
            'media_category': self.media_category,
            'additional_owners': additional_owners
        })

        self.media_id: str = r['media_id_string']

        return r

    def _append(self, media: bytes, segment_index: int) -> bool:
        """Upload a chunk of the media file."""
        return self._request('POST', {
            'command': 'APPEND',
            'media_id': self.media_id,
            'segment_index': segment_index
        }, files={'media': media})

    def _finalize(self) -> dict:
        """Complete the upload."""
        return self._request('POST', {
            'command': 'FINALIZE',
            'media_id': self.media_id
        })

    def _get_status(self) -> dict:
        """Updates media processing operation."""
        return self._request('GET', params={
            'command': 'STATUS',
            'media_id': self.media_id
        })

    def _set_media_category(self, ext: str, use_case: str) -> None:
        self.media_category: str = {
            '.mp4': {
                'tweet': 'TweetVideo',
                'dm': 'DmVideo'
            },
            '.gif': {
                'tweet': 'TweetGif',
                'dm': 'DmGif'
            }
        }[ext][use_case]

    def _chunk(self, chunk_size: int = 5242880) -> Iterator[bytes]:
        with open(self.file, 'rb') as f:
            while media := f.read(chunk_size):
                yield media

    def upload_media(self, file: str, use_case: str,
                     additional_owners: list = None) -> dict:
        """
        Chunked media upload.

        :param file: File to upload: mp4 or gif.
        :param use_case: Use case of the file to be uploaded: tweet or dm.
        :param additional_owners: A comma-separated list of user IDs
            to set as additional owners allowed to use the returned media_id
            in Tweets or Cards. Up to 100 additional owners may be specified.
        """
        ext = splitext(file)[1].lower()
        if ext not in ['.mp4', '.gif']:
            raise TCUError('Unsupported file format.')
        if use_case not in ['tweet', 'dm']:
            raise TCUError('Invalid use case.')

        self.file = abspath(file)
        self._set_media_category(ext, use_case)
        self._init(additional_owners)
        for i, media in enumerate(self._chunk()):
            self._append(media, i)
        r = self._finalize()
        if 'processing_info' in r:
            while r['processing_info']['state'] != 'succeeded':
                sleep(r['processing_info']['check_after_secs'])
                r = self._get_status()
                if r['processing_info']['state'] == 'failed':
                    raise TCUError(r['processing_info']['error'])

        return r
