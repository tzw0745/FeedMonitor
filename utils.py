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
