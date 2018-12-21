#!/bin/bash/python3
from aiohttp import web
from geoclient import WEBAPP_HOST, WEBAPP_PORT, WEBHOOK_URL_PATH
from geoclient.wellfield import dp, get_new_configured_app

if __name__ == '__main__':
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)

