"""
Provides FileStorage implementation for local filesystem.

This is usefull for storing files inside a local path.

"""
import os
import uuid
import shutil
import mimetypes
import json
from datetime import datetime

from .interfaces import FileStorage, StoredFile
from . import utils


class LocalStoredFile(StoredFile):
    def __init__(self, file_id, local_path):
        _check_file_id(file_id)

        self._metadata_path = _metadata_path(local_path)
        self._file_path = _file_path(local_path)
        self._file = None

        try:
            metadata = open(self._metadata_path, 'r')
        except:
            raise IOError('File %s not existing' % file_id)

        metadata_info = {'filename': 'unknown',
                         'content_type': 'application/octet-stream',
                         'last_modified': None}
        with metadata:
            try:
                metadata_content = metadata.read()
                metadata_info.update(json.loads(metadata_content))

                last_modified = metadata_info['last_modified']
                if last_modified:
                    metadata_info['last_modified'] = datetime.strptime(last_modified,
                                                                       '%Y-%m-%d %H:%M:%S')
            except Exception:
                raise ValueError('Invalid file metadata for %s' % file_id)

        super(LocalStoredFile, self).__init__(file_id=file_id, **metadata_info)

    def read(self, n=-1):
        if self._file is None:
            self._file = open(self._file_path, 'rb')
        return self._file.read(n)


class LocalFileStorage(FileStorage):
    def __init__(self, storage_path):
        self.storage_path = storage_path

    def __local_path(self, fileid):
        return os.path.join(self.storage_path, fileid)

    def get(self, file_or_id):
        fileid = self.fileid(file_or_id)
        local_file_path = self.__local_path(fileid)
        return LocalStoredFile(fileid, local_file_path)

    def __save_file(self, file_id, content, filename, content_type=None):
        local_file_path = self.__local_path(file_id)

        if content_type is None:
            guessed_type = mimetypes.guess_type(filename, strict=False)[0]
            content_type = guessed_type or 'application/octet-stream'

        os.makedirs(local_file_path)
        metadata = {'filename': filename,
                    'content_type': content_type,
                    'last_modified': utils.timestamp()}

        with open(_metadata_path(local_file_path), 'w') as metadatafile:
            metadatafile.write(json.dumps(metadata))

        if hasattr(content, 'read'):
            with open(_file_path(local_file_path), 'wb') as fileobj:
                shutil.copyfileobj(content, fileobj)
        else:
            with open(_file_path(local_file_path), 'wb') as fileobj:
                fileobj.write(content)

    def create(self, content, filename, content_type=None):
        new_file_id = str(uuid.uuid1())
        self.__save_file(new_file_id, content, filename, content_type)
        return new_file_id

    def replace(self, file_or_id, content, filename=None, content_type=None):
        fileid = self.fileid(file_or_id)
        _check_file_id(fileid)

        # First check file existed and we are not using replace
        # as a way to force a specific file id on creation.
        if not self.exists(fileid):
            raise IOError('File %s not existing' % file_or_id)

        if filename is None:
            filename = self.get(fileid).filename

        self.delete(fileid)
        self.__save_file(fileid, content, filename, content_type)
        return fileid

    def delete(self, file_or_id):
        fileid = self.fileid(file_or_id)
        _check_file_id(fileid)

        local_file_path = self.__local_path(fileid)
        try:
            shutil.rmtree(local_file_path)
        except:
            pass

    def exists(self, file_or_id):
        fileid = self.fileid(file_or_id)
        _check_file_id(fileid)

        local_file_path = self.__local_path(fileid)
        return os.path.exists(local_file_path)


def _check_file_id(file_id):
    # Check that the given file id is valid, this also
    # prevents unsafe paths.
    try:
        uuid.UUID('{%s}' % file_id)
    except:
        raise ValueError('Invalid file id %s' % file_id)


def _metadata_path(local_path):
    return os.path.join(local_path, 'metadata.json')


def _file_path(local_path):
    return os.path.join(local_path, 'file')