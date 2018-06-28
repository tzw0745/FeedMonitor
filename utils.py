# coding:utf-8
"""
Created by tzw0745 at 2016/11/22.
"""


def send_mail(address, subject, content,
              email, password,
              smtp_address=None, smtp_port=None,
              html=False):
    """
    发送电子邮件
    :param address: 收件人
    :param subject: 邮件主题
    :param content: 邮件内容
    :param email: 用户名
    :param password: 密码
    :param smtp_address: smtp服务器地址，可选
    :param smtp_port: smtp服务器端口号，可选
    :param html: 是否以html代码形式发送邮件，可选
    :return: 无
    """
    smtp_map = {'qq.com': ('smtp.qq.com', 465),
                '163.com': ('smtp.163.com', 465)}
    if smtp_address is None or smtp_port is None:
        for tail in smtp_map:
            if email.endswith(tail):
                smtp_address, smtp_port = smtp_map[tail]
                break
        else:
            raise KeyError('smtp server and port not found')

    import smtplib
    m = smtplib.SMTP_SSL(smtp_address, smtp_port)
    m.login(email, password)

    from email.mime.text import MIMEText
    if html:
        msg = MIMEText(content, 'html', 'utf-8')
    else:
        msg = MIMEText(content)
    msg['from'] = email
    msg['to'] = address
    msg['subject'] = subject
    m.sendmail(email, address, str(msg))

    m.quit()


def parse_id(identity_num):
    """
    解析身份证号
    :param identity_num: 18位居民身份证号
    :return: 字典
    """
    identity_num = str(identity_num).strip()
    import re
    if not re.match(r'[0-9Xx]{18}', identity_num):
        raise ValueError('身份证号格式错误')
    # 用倒数第二位获取性别
    if int(identity_num[16]) % 2 == 1:
        gender = 'm'
    else:
        gender = 'f'
    # 获取生日
    import datetime
    birth = datetime.datetime.strptime(identity_num[6:14], '%Y%m%d')
    # 用前六位获取籍贯
    import gb2260
    try:
        address = str(gb2260.get(identity_num[:6]))
        address = address.split(' ')[-1].replace('/', '')[:-1]
    except ValueError:
        address = ''

    return {'gender': gender,
            'birth': '{:%F}'.format(birth),
            'address': address}


def express100(com, num):
    """
    用快递100的api查询快递信息
    :param com: 公司名称
    :param num: 快递单号
    :return: [(time, info),...]
    """
    e2c = {'ems': 'ems',
           'debangwuliu': '德邦',
           'guotongkuaidi': '国通',
           'huitongkuaidi': '汇通',
           'quanfengkuaidi': '全峰',
           'rufengda': '如风达',
           'shunfeng': '顺丰',
           'yuantong': '圆通',
           'yunda': '韵达',
           'shentong': '申通',
           'zhaijisong': '宅急送',
           'zhongtong': '中通'}
    c2e = {}
    for key in e2c:
        c2e[e2c[key]] = key

    if com in c2e:
        com = c2e[com]
    else:
        return {'error': '快递公司错误'}

    url = 'http://www.kuaidi100.com/query?type={}&postid={}'
    url = url.format(com, num)

    import requests
    express = requests.get(url).json()
    if express['status'] != '200':
        return {'error': express['message']}

    result = []
    for entry in express['data']:
        result.append((entry['time'], entry['context']))
    result.reverse()

    return {'data': result}


def is_colorful_img(img):
    """
    判断图像是否为彩色图像
    :param img: PIL.Image.Image，目标图像
    :return: 目标图像为彩色图像时为True，反之为False
    """
    if img.mode in ['1', 'L']:
        return False

    img_rgb = img.convert('RGB')
    for pixel in img_rgb.getdata():
        if not pixel[0] == pixel[1] == pixel[2]:
            return True

    return False


def func_timer(func, repeat=1, **params):
    """
    获取目标函数运行时间
    :param func: 目标函数
    :param repeat: 目标函数重复运行次数
    :param params: 目标函数所需参数
    :return: 目标函数重复运行repeat次评价所需要的时长，单位为秒
    """
    import timeit
    import functools

    return timeit.timeit(functools.partial(
        func, **params), number=repeat) / repeat


def func_retry(func, accept_error=Exception, retry=3,
               interval=1, fallback=print, **params):
    """
    重复执行函数，直到函数执行成功或达到重试次数上限
    :param func: 待执行函数
    :param accept_error: 可接受的函数错误
    :param retry: 重试次数上限
    :param interval: 函数调用失败时的延时，单位为秒
    :param fallback: 当达到重试上限时调用的函数
    :param params: 待执行函数接收参数
    :return: 函数成功执行结果
    """
    if retry <= 0:
        raise ValueError('arg "retry" should greater than 0')
    if interval <= -1:
        raise ValueError('arg "interval" should greater than -1')

    error_backup = None
    for i in range(retry):
        try:
            return func(**params)
        except accept_error as _accept_error:
            error_backup = _accept_error
    else:
        fallback(error_backup)


class CONST:
    """
    常量类
    """

    class ConstError(TypeError):
        pass

    class ConstCaseError(ConstError):
        pass

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("can't change const %s" % name)
        if not name.isupper():
            raise self.ConstCaseError('const name "%s" is not all uppercase' % name)
        self.__dict__[name] = value
