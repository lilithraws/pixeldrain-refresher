import asyncio
import httpx
import base64
import os
import logging
import json
import re
import secrets
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO)

load_dotenv()
key_b64 = base64.b64encode((':' + os.environ['API_KEY']).encode())

finding_logger = logging.getLogger('finding')
refreshing_logger = logging.getLogger('refreshing')

finding_scheduler = AsyncIOScheduler()

def refresher(id):
    refreshing_logger.debug(f'File ID : {id}')
    try:
        file_viewer_response = httpx.get(f'https://pixeldrain.com/u/{id}')
        if file_viewer_response.status_code == 200:
            try:
                view_token = re.findall(r'"view_token":"(.+)",', file_viewer_response.content.decode())[0]
                refreshing_logger.debug(f'View Token : {view_token}')
                if not "".__eq__(view_token):
                    payload = {
                        'token': view_token,
                    }
                    view_response = httpx.post(f'https://pixeldrain.com/api/file/{id}/view', data=payload)
                    if view_response.status_code == 200:
                        try:
                            view_result = json.loads(view_response.content)
                            if view_result['success'].__eq__(True):
                                refreshing_logger.info(f'{id} View succeed.')
                            else:
                                raise TypeError
                        except (json.decoder.JSONDecodeError, TypeError):
                            refreshing_logger.info(f'{id} View failed.')
                    else:
                        raise httpx.HTTPStatusError
            except IndexError:
                refreshing_logger.warning(id + 'Cannot find view token.')
        else:
            raise httpx.HTTPStatusError
    except (httpx.HTTPError, httpx.HTTPStatusError):
        refreshing_logger.error('Pixeldrain is unavailable or blocking us.')

    time.sleep(secrets.randbelow(500) / 100)

async def refresh(refreshing_queue, refreshing_executor):
    while True:
        (id) = await refreshing_queue.get()
        future = refreshing_executor.submit(refresher, id)
        await asyncio.wrap_future(future)
        refreshing_queue.task_done()

def files_need_refresh_filter(obj):
    last_view = datetime.now(timezone.utc)
    try:
        last_view = datetime.strptime(obj['date_last_view'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        last_view = datetime.strptime(obj['date_last_view'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - last_view).days > 30

async def find(refreshing_queue):
    async with httpx.AsyncClient() as client:
        headers = {
            'Authorization': "Basic " + key_b64.decode(),
        }
        try:
            response = await client.get('https://pixeldrain.com/api/user/files', headers=headers)
            if response.status_code == 200:
                finding_logger.info('Fetching file list succeed.')
                try:
                    files = json.loads(response.content)['files']
                    finding_logger.info(f'Parsing file list succeed. There\'s totally {len(files)} files.')
                    need_to_refresh = list(filter(files_need_refresh_filter, files))
                    if need_to_refresh:
                        finding_logger.info(f'{len(need_to_refresh)} files need to refresh. Adding to refreshing queue.')
                        for _file in need_to_refresh:
                            refreshing_queue.put_nowait(_file['id'])
                    else:
                        finding_logger.info(f'No files need to refresh.')
                except (json.decoder.JSONDecodeError, TypeError) as ex:
                    finding_logger.error('File list parsing failed. Pixeldrain may be misfunctional.')
                    finding_logger.error(ex)
            elif response.status_code == 401:
                finding_logger.warning('Fetching file list failed, wrong api key may be set.')
            else:
                finding_logger.warning('Unknown error. Pixeldrain may be unavailable.')
        except httpx.HTTPError:
            finding_logger.error('Pixeldrain is unavailable.')

    finding_logger.info(f'Next finding at {finding_scheduler.get_jobs()[0].next_run_time}')

async def main():
    refreshing_queue = asyncio.Queue()
    refreshing_executor = ThreadPoolExecutor(max_workers=10)
    for _ in range(10):
        asyncio.create_task(refresh(refreshing_queue, refreshing_executor))

    finding_scheduler.start()
    finding_scheduler.add_job(find, args=[refreshing_queue])
    finding_scheduler.add_job(find, CronTrigger.from_crontab('0 0 * * *'), args=[refreshing_queue])
    while True:
        await asyncio.sleep(1000)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass