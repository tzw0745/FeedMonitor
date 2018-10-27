# coding:utf-8
"""
Created by tzw0745 at 2018/6/11.
"""
import argparse
import logging
import time
import traceback
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime

import feedparser
import requests
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from utils import send_mail, func_retry


def load_config(cfg_path):
    """
    读取ini配置文件
    :param cfg_path: ini文件路径
    :return: 配置字典
    """
    cfg_parser = ConfigParser(strict=False, interpolation=None)
    cfg_parser.read(cfg_path)

    _ = defaultdict(dict)
    for section in cfg_parser.sections():
        for option in cfg_parser.options(section):
            _[section][option] = cfg_parser.get(section, option)
    # check config params
    keys = {'MySQL', 'Email', 'Feeds'}
    assert set(_.keys()) & keys == keys
    keys = {'host', 'database', 'charset', 'username', 'password'}
    assert set(_['MySQL'].keys()) & keys == keys
    keys = {'receiver', 'username', 'password'}
    assert set(_['Email'].keys()) & keys == keys
    assert len(_['Feeds'].keys()) > 0

    return _


def insert_mysql(engine_cfg: dict, table_name: str, articles_map: dict):
    """
    将多条feed数据插入至MySQL
    :param engine_cfg: 数据库连接配置字典
    :param table_name: 数据表名称
    :param articles_map: 文章字典
    :return: None
    """
    global logger
    engine = create_engine(URL(**engine_cfg))
    base = declarative_base()

    class Template(base):
        __tablename__ = table_name
        id = Column(Integer, primary_key=True, autoincrement=True)
        link = Column(String(255), unique=True, nullable=False)
        pub_dt = Column(DateTime, nullable=False)
        title = Column(String(100), nullable=False)
        summary = Column(String(100), nullable=True)
        tags = Column(String(100), nullable=True)
        read_flag = Column(Boolean, default=False, nullable=False)

    base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    for entity in session.query(Template).filter(
            Template.link.in_(articles_map.keys())):
        if entity.pub_dt < articles_map[entity.link]['pub_dt']:
            session.delete(entity)
        else:
            del articles_map[entity.link]
    if not articles_map:
        return

    links = articles_map.keys()
    logger.warning('insert {} items into table {!r}'.format(
        len(links), table_name))
    for link in sorted(links, key=lambda k: articles_map[k]['pub_dt']):
        new_entity = Template(**articles_map[link])
        session.merge(new_entity)
    session.commit()


def main():
    global args, cfg_map, logger
    logger.warning('config connection: mysql://{0[username]}:***@{0[host]}'
                   '/{0[database]}'.format(cfg_map['MySQL']))

    engine_map = dict(cfg_map['MySQL'])
    engine_map.update({
        'drivername': 'mysql',
        'query': {'charset': engine_map['charset']}
    })
    del engine_map['charset']

    while True:
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                                 ' AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/69.0.3497.100 Safari/537.36'}
        for feed_name in sorted(cfg_map['Feeds'].keys()):
            log_str = 'get response from {}'.format(feed_name)
            url = cfg_map['Feeds'][feed_name]
            cookies_str = cfg_map.get('Cookies', {}).get(feed_name, None)
            cookies = dict(kv.split('=', 1) for kv in cookies_str.split('; ')) \
                if cookies_str else None
            response = func_retry(
                requests.get, url=url, timeout=3, accept_error=requests.RequestException,
                fallback=lambda _: logger.error(log_str + ' fail: ' + str(_)),
                cookies=cookies, headers=headers
            )
            if not response:
                continue
            if response.status_code != 200:
                logger.error('{} is unavailable now'.format(feed_name))
                continue
            content = response.content
            logger.info('{}, content length: {}'.format(log_str, len(content)))

            feed_parser = feedparser.parse(content)
            if not feed_parser.entries:
                logger.error('{} return empty entries'.format(feed_name))
                continue
            logger.info('newest one: {}'.format(feed_parser.entries[0]['title']))

            feed_info_map = {}
            for entity in feed_parser.entries:
                feed_info_map[entity['link']] = {
                    'link': entity['link'],
                    'pub_dt': datetime.fromtimestamp(
                        time.mktime(entity['updated_parsed'])
                    ),
                    'title': entity['title'].strip(),
                    'summary': entity['summary'].strip(),
                    'tags': ','.join(tag['term'] for tag in entity['tags']).strip()
                }
            insert_mysql(engine_map, feed_name.upper(), feed_info_map)

        time.sleep(int(args.interval) * 60)


# region arg parser
parser = argparse.ArgumentParser(
    description='Monitor Rss Feed and Store into MySQL'
)
parser.add_argument(
    '-l', '--log-level', dest='log_level', help='set python logging level',
    choices={'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}, default='INFO'
)
parser.add_argument(
    '-i', '--interval', dest='interval', default=10,
    help='set interval of feed request, unit: minutes. [1~100]',
)
parser.add_argument(
    dest='config_file', help='ini config file path'
)
args = parser.parse_args()
if not 1 <= int(args.interval) <= 100:
    raise ValueError('interval show between 1~10')
# endregion

# region logger
log_format = '[%(asctime)s %(levelname)s] %(message)s'
handle = logging.StreamHandler()
handle.setFormatter(logging.Formatter(log_format))
level = logging.getLevelName(args.log_level)
logger = logging.getLogger()
logger.addHandler(handle)
logger.setLevel(level)
# endregion

# region load config file
try:
    cfg_map = load_config(args.config_file)
except Exception:
    logger.critical('load config file fail')
    raise
# endregion


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical('\n'.join([str(e), traceback.format_exc()]))
        if 'Email' in cfg_map.keys() and False:
            _ = cfg_map['Email']
            send_mail(_['receiver'], 'Feed Monitor Down',
                      traceback.format_exc(), _['username'], _['password'])
        raise
