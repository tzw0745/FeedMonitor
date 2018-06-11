# coding:utf-8
"""
Created by tzw0745 at 2018/6/11.
"""
import time
import logging
import traceback
from datetime import datetime
from collections import defaultdict
from configparser import ConfigParser

import pymysql
import requests
import feedparser

from utils import send_mail

log_format = '[%(asctime)s %(levelname)s] %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)

cfg_map = {}


def insert_mysql(table_name, entries):
    """
    将多条feed数据插入至MySQL
    :param table_name: 表名
    :param entries: feed数据列表
    :return: None
    """
    _ = cfg_map['MySQL']
    conn = pymysql.connect(_['host'], _['username'], _['password'],
                           _['database'], charset=_['charset'])
    cursor = conn.cursor()

    # create table
    sql = 'SHOW TABLES LIKE "{}"'.format(table_name)
    cursor.execute(sql)
    if not cursor.fetchall():
        logging.warning('table {} not exists, try to create'
                        .format(table_name))
        sql = '''CREATE TABLE {} (
            link      varchar(255) PRIMARY KEY NOT NULL,
            pub_dt    datetime                 NOT NULL,
            title     varchar(100)             NOT NULL,
            summary   varchar(100),
            tags      varchar(50),
            read_flag tinyint(1)               NOT NULL
        )'''.format(table_name)
        cursor.execute(sql)
        conn.commit()

    # filter with last published datetime
    sql = 'SELECT pub_dt FROM {} ORDER BY pub_dt DESC LIMIT 1' \
        .format(table_name)
    cursor.execute(sql)
    result = cursor.fetchall()
    last_pub_dt = result[0][0] if result else None
    values = []
    for entity in entries:
        if not last_pub_dt or last_pub_dt < entity[1]:
            entity[1] = entity[1].strftime('%Y-%m-%d %H:%M:%S')
            values.append(entity)

    sql = 'INSERT INTO {} VALUES (%s, %s, %s, %s, %s, FALSE)' \
        .format(table_name)
    try:
        if not values:
            return
        cursor.executemany(sql, values)
        conn.commit()
        logging.warning('insert {} entries to {}'
                        .format(len(values), table_name))
    except Exception as e:
        conn.rollback()
        logging.critical('insert {} entries to {} fail, {}'
                         .format(len(values), table_name, str(e)))
        raise e
    finally:
        conn.close()


def main():
    global cfg_map
    cfg_map = load_config()
    logging.info('load config: MySQL://{0[username]}@{0[host]}:'
                 '3306/{0[database]}'.format(cfg_map['MySQL']))

    while True:
        for feed in sorted(cfg_map['Feeds'].keys()):
            url = cfg_map['Feeds'][feed]
            content = requests.get(url).content
            logging.info('get response from {}, content length: {}'
                         .format(feed, len(content)))

            entries = [[
                entity['link'],
                datetime.fromtimestamp(time.mktime(entity['updated_parsed'])),
                entity['title'],
                entity['summary'],
                ','.join(tag['term'] for tag in entity['tags'])
            ] for entity in feedparser.parse(content).entries]

            insert_mysql(feed.upper(), entries)

        time.sleep(10 * 60)


def load_config():
    cfg_parser = ConfigParser()
    cfg_parser.read('config.ini')

    _ = defaultdict(dict)
    for section in cfg_parser.sections():
        for option in cfg_parser.options(section):
            _[section][option] = cfg_parser.get(section, option)
    # check config params
    assert not set(_.keys()).difference(('MySQL', 'Email', 'Feeds'))
    assert not set(_['MySQL'].keys()).difference((
        'host', 'database', 'charset', 'username', 'password'
    ))
    assert not set(_['Email'].keys()).difference((
        'receiver', 'username', 'password'
    ))
    assert len(_['Feeds'].keys()) > 0

    return _


if __name__ == '__main__':
    try:
        print(time.asctime().rjust(80, '-'))
        main()
        print('\nall done')
    except Exception as e:
        print(''.join([str(e), traceback.format_exc()]))
        if 'Email' in cfg_map:
            _ = cfg_map['Email']
            send_mail(_['receiver'], 'Feed Monitor Down',
                      traceback.format_exc(),
                      _['username'], _['password'])
    finally:
        print(time.asctime().rjust(80, '-'))
