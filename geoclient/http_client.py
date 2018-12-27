import os
import sys
import json
import base64
from typing import Optional
from geoclient import API_URL
import multiprocessing as mp

from requests import request as make_request

#: Словарь HTTP-заголовков для каждого запроса к API
HEADERS = {'Content-Type': 'application/json'}


def get(url, params=None, **kwargs):
    return request('get', url, params=params, **kwargs)


def post(url, data=None, json=None, **kwargs):
    return request('post', url, data=data, json=json, **kwargs)


def put(url, data=None, **kwargs):
    return request('put', url, data=data, **kwargs)


def delete(url, data=None, **kwargs):
    return request('delete', url, data=data, **kwargs)


def request(method, url, **kwargs):
    # check URL relativity
    if 'http://' not in url:
        url = API_URL + url

    # init headers with default 'application/json' if None given
    if 'headers' not in kwargs:
        kwargs['headers'] = {}

    kwargs['headers'].update(HEADERS)

    # use no 'Content-Type' for files upload as it is stated in requests as default parameter
    if 'files' in kwargs and kwargs['files'] and 'Content-Type' in kwargs['headers']:
        del kwargs['headers']['Content-Type']

    return make_request(method, url, **kwargs)


def get_app_versions_from_geoclient():
    res = get('/available_app_versions').json()
    if res['status'] == 200:
        return res['items']
    else:
        raise ValueError


def get_wellfields_from_geoclient():
    res = get('/available_wellfields').json()
    if res['status'] == 200:
        return res['items']
    else:
        raise ValueError


def _is_wellfield_exist(app_version, prefix, name):
    res = post('/is_wellfield_exist', data=json.dumps(dict(app_version=app_version, name=name, prefix=prefix))).json()
    if res['status'] == 200:
        return res['exist']
    else:
        raise ValueError


def _create_wellfield_in_separate_process(app_version, prefix, name):
    if os.fork() != 0:
        return
    post('/create_wellfield', data=json.dumps(dict(app_version=app_version, name=name, prefix=prefix))).json()
    sys.exit(0)


def create_wellfield(app_version, prefix, name):
    p = mp.Process(target=_create_wellfield_in_separate_process, args=(app_version, prefix, name))
    p.start()
