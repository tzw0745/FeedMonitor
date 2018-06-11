# coding:utf-8
"""
Created by tzw0745 at 2018/6/11.
"""
import time
import logging
import argparse
import traceback
from datetime import datetime
from collections import defaultdict
from configparser import ConfigParser

import pymysql
import requests
import feedparser

from utils import send_mail


def load_config(cfg_path):
    """
    读取ini配置文件
    :param cfg_path: ini文件路径
    :return: 配置字典
    """
    cfg_parser = ConfigParser()
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


def insert_mysql(host, database, username, password,
                 table_name, entries, charset='utf8'):
    """
    将多条feed数据插入至MySQL
    :param host: MySQL主机位置
    :param database: MySQL数据库名称
    :param username: 用户名
    :param password: 密码
    :param table_name: 表名
    :param entries: feed数据列表
    :param charset: 数据库字符集，默认为utf8
    :return: None
    """
    global logger
    conn = pymysql.connect(host, username, password,
                           database, charset=charset)
    cursor = conn.cursor()
    logger.info('MySQL connected')

    # create table
    sql = 'SHOW TABLES LIKE "{}"'.format(table_name)
    cursor.execute(sql)
    if not cursor.fetchall():
        logger.warning('table {} not exists, try to create'
                       .format(table_name))
        sql = '''CREATE TABLE {} (
            id        INT AUTO_INCREMENT,
            link      VARCHAR(255) NOT NULL,
            pub_dt    DATETIME     NOT NULL,
            title     VARCHAR(100) NOT NULL,
            summary   VARCHAR(100) NULL,
            tags      VARCHAR(50)  NULL,
            read_flag TINYINT(1)   NOT NULL,
            PRIMARY KEY (id, link)
        )'''.format(table_name)
        cursor.execute(sql)
        conn.commit()

    sql = 'SELECT link FROM {} WHERE link in {}'.format(
        table_name, tuple(entity[0] for entity in entries))
    cursor.execute(sql)
    exists_links = tuple(x[0] for x in cursor.fetchall())
    entries = list(filter(lambda x: x[0] not in exists_links, entries))

    sql = 'INSERT INTO {} VALUES (NULL, %s, %s, %s, %s, %s, FALSE)' \
        .format(table_name)
    try:
        if not entries:
            return
        cursor.executemany(sql, entries)
        conn.commit()
        logger.warning('insert {} entries to {}'
                       .format(len(entries), table_name))
    except Exception as e:
        conn.rollback()
        logger.critical('insert {} entries to {} fail: {}'
                        .format(len(entries), table_name, str(e)))
        raise e
    finally:
        conn.close()
        logger.info('MySQL connection close')


def main():
    global args, cfg_map, logger
    logger.warning('load config: MySQL://{0[username]}@{0[host]}:'
                   '3306/{0[database]}'.format(cfg_map['MySQL']))

    while True:
        for feed in sorted(cfg_map['Feeds'].keys()):
            url = cfg_map['Feeds'][feed]
            content = requests.get(url).content
            logger.info('get response from {}, content length: {}'
                        .format(feed, len(content)))

            entries = [[
                entity['link'],
                entity['updated_parsed'],
                entity['title'],
                entity['summary'],
                ','.join(tag['term'] for tag in entity['tags'])
            ] for entity in feedparser.parse(content).entries]
            entries = list(reversed(entries))
            logger.info('newest one: {}'.format(entries[-1][2]))

            _ = cfg_map['MySQL']
            insert_mysql(_['host'], _['database'], _['username'],
                         _['password'], feed.upper(), entries, _['charset'])

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
except Exception as e:
    logger.critical('load config file fail: ' + str(e))
    raise

# endregion


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.critical(''.join([str(e), traceback.format_exc()]))
        send_mail(cfg_map['Email']['receiver'],
                  'Feed Monitor Down', traceback.format_exc(),
                  cfg_map['Email']['username'], cfg_map['Email']['password'])
        raise
