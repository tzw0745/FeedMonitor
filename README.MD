# FeedMonitor
## What This Project Do
1. send http request to rss feed url
2. parser xml content
3. save newer item to MySQL

## How To Use
1. requirements
  [requests](http://docs.python-requests.org/en/master/), [feedparser](https://pythonhosted.org/feedparser/), [SQLAlchemy](http://www.sqlalchemy.org/), [MySQLClient](https://pypi.org/project/mysqlclient/)
2. custom module
  [utils.py](https://github.com/tzw0745/FeedMonitor/blob/master/utils.py) `send_email()`(send notice email when service is down, use SMTP protocol), `func_retry()`(repeat function until succeed or reaches the maximum retries)
3. create config file
  ```ini
  [MySQL]
  host = 127.0.0.1
  database = feed_monitor
  charset = utf8
  username = user
  password = pwd

  [Email]
  receiver = receiver@domain.com
  username = sender@domain.com
  password = email_pwd

  [Feeds]
  feed_name1 = https://domain1.com/feed
  feed_name2 = https://domain2.com/feed
  ```
4. start service
  ```
  feed_monitor.py [-h] [-l {INFO,ERROR,DEBUG,WARNING,CRITICAL}]
                         [-i INTERVAL]
                         config_file
  ```

## MySQL Design
1. table design
  ```sql
  CREATE TABLE FEED_NAME_UPPER (
	  id INTEGER NOT NULL AUTO_INCREMENT, 
	  link VARCHAR(255), 
	  pub_dt DATETIME, 
	  title VARCHAR(100), 
	  summary VARCHAR(100) NULL, 
	  tags VARCHAR(100) NULL, 
	  read_flag BOOL, 
	  PRIMARY KEY (id), 
	  UNIQUE (link), 
	  CHECK (read_flag IN (0, 1))
  )
  ```
2. xml data extract
  ```python
  sql = 'REPLACE INTO FEED_NAME_UPPER VALUES (NULL, %s, %s, %s, %s, %s, FALSE)'
  value = (entity['link'], entity['updated_parsed'], entity['title'], entity['summary'],
           ','.join(tag['term'] for tag in entity['tags']))
  # entity foreach feedparser.parse(content).entries
  ```

3. newer item controller
  ```python
  if entity['link'] not in FEED_NAME_UPPER table:
    # insert into MySQL
  else:
    if entity['updated_parsed'] > FEED_NAME_UPPER['pub_dt']:
      # replace into MySQL

  ```