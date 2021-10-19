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
        self._session = Session()
        self._session.auth = auth
        self.file = None
        self._media_id = None

    def _request(self, method, data=None, params=None, files=None):
        try:
            response = self._session.request(
                method, TChunkedUpload.RESOURCE_URL, params, data,
                files=files
            )
        finally:
            self._session.close()

        if not response.ok:
            raise TCUError(response.json()['errors'])

        if response.status_code == 204:
            return True

        return response.json()

    def _init(self, media_category: str,
              additional_owners: list = None) -> dict:
        """Initiate a file upload session."""
        r = self._request('POST', {
            'command': 'INIT',
            'total_bytes': getsize(self.file),
            'media_type': guess_type(self.file)[0],
            'media_category': media_category,
            'additional_owners': additional_owners
        })

        self._media_id: str = r['media_id_string']

        return r

    def _append(self, media: bytes, segment_index: int) -> bool:
        """Upload a chunk of the media file."""
        return self._request('POST', {
            'command': 'APPEND',
            'media_id': self._media_id,
            'segment_index': segment_index
        }, files={'media': media})

    def _finalize(self) -> dict:
        """Complete the upload."""
        return self._request('POST', {
            'command': 'FINALIZE',
            'media_id': self._media_id
        })

    def _get_status(self) -> dict:
        """Updates media processing operation."""
        return self._request('GET', params={
            'command': 'STATUS',
            'media_id': self._media_id
        })

    def _iter_file(self, chunk_size: int = 5242880) -> Iterator[bytes]:
        with open(self.file, 'rb') as f:
            while chunk := f.read(chunk_size):
                yield chunk

    def upload_media(self, file: str, media_category: str,
                     additional_owners: list = None) -> dict:
        """
        Chunked media upload.

        :param file: File to upload: mp4 or gif.
        :param media_category: A string enum value which identifies
            a media use case. This identifier is used to enforce use
            case specific constraints and enable advanced features.
        :param additional_owners: A comma-separated list of user IDs
            to set as additional owners allowed to use the returned
            media_id in Tweets or Cards. Up to 100 additional owners
            may be specified.
        """
        if splitext(file)[1].lower() not in ['.mp4', '.gif']:
            raise TCUError('Unsupported file format.')
        self.file: str = abspath(file)
        self._init(media_category, additional_owners)
        for i, media in enumerate(self._iter_file()):
            self._append(media, i)
        r = self._finalize()
        if 'processing_info' in r:
            while r['processing_info']['state'] != 'succeeded':
                sleep(r['processing_info']['check_after_secs'])
                r = self._get_status()
                if r['processing_info']['state'] == 'failed':
                    raise TCUError(r['processing_info']['error'])

        return r
