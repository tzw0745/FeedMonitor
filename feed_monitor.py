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


def main():
    cfg_map = load_config()
    logging.info('load config: MySQL://{0[username]}@{0[host]}:'
                 '3306/{0[database]}'.format(cfg_map['MySQL']))


def load_config():
    cfg_parser = ConfigParser()
    cfg_parser.read('config.ini')

    cfg_map = defaultdict(dict)
    for section in cfg_parser.sections():
        for option in cfg_parser.options(section):
            cfg_map[section][option] = cfg_parser.get(section, option)
    # check config
    assert not set(cfg_map.keys()).difference(('MySQL', 'Email', 'Feed'))
    return cfg_map


if __name__ == '__main__':
    try:
        print(time.asctime().rjust(80, '-'))
        main()
        print('\nall done')
    except Exception as e:
        print(''.join([str(e), traceback.format_exc()]))
    finally:
        print(time.asctime().rjust(80, '-'))
