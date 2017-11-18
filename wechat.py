from pyqrcode import QRCode
from socket import timeout as timeout_error
import http.cookiejar
import json
import logging
import random
import re
import ssl
import sys
import time
import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import xml.dom.minidom

class WeChat(object):
    def __init__(self):
        self.app_id = 'wx782c26e4c19acffb'
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.lang = 'zh_CN'
        self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.109 Safari/537.36'

        self.base_uri = ''
        self.base_request = {}
        self.pass_ticket = ''
        self.redirect_uri = ''
        self.sid = ''
        self.skey = ''
        self.uin = ''
        self.uuid = ''
        self.group_ids = []
        self.groups = []

        self.cookie = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookie))
        opener.addheaders = [('User-agent', self.user_agent)]
        urllib.request.install_opener(opener)

    def getUUID(self):
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': self.app_id,
            'fun': 'new',
            'lang': self.lang,
            '_': int(time.time()),
        }
        data = self._post(url, params, False).decode("utf-8")

        if data == '':
            return False

        matches = re.search(r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"', data)
        if matches:
            code = matches.group(1)
            self.uuid = matches.group(2)
            return code == '200'
        return False

    def genQRCode(self):
        qr_code = QRCode('https://login.weixin.qq.com/l/' + self.uuid)
        qr_data = qr_code.text(1)

        try:
            b = u'\u2588'
            sys.stdout.write(b + '\r')
            sys.stdout.flush()
        except UnicodeEncodeError:
            white = 'MM'
        else:
            white = b
        black = '  '
        block_count = int(2)
        if abs(block_count) == 0:
            block_count = 1
        white *= abs(block_count)
        if block_count < 0:
            white, black = black, white
        sys.stdout.write(' ' * 50 + '\r')
        sys.stdout.flush()
        qr = qr_data.replace('0', white).replace('1', black)
        sys.stdout.write(qr)
        sys.stdout.flush()

    def waitForLogin(self, tip=1):
        time.sleep(tip)
        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
            tip, self.uuid, int(time.time()))
        data = self._get(url)

        if data == '':
            return False

        matches = re.search(r"window.code=(\d+);", data)
        code = matches.group(1)

        if code == '201':
            return True
        elif code == '200':
            matches = re.search(r'window.redirect_uri="(\S+?)";', data)
            r_uri = matches.group(1) + '&fun=new'
            self.redirect_uri = r_uri
            self.base_uri = r_uri[:r_uri.rfind('/')]
            return True
        elif code == '408':
            print('Login timeout')
        else:
            print('Login failed')
        return False

    def login(self):
        data = self._get(self.redirect_uri)

        if data == '':
            return False

        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement

        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if '' in (self.skey, self.sid, self.uin, self.pass_ticket):
            return False

        self.base_request = {
            'Uin': int(self.uin),
            'Sid': self.sid,
            'Skey': self.skey,
            'DeviceID': self.deviceId,
        }

        return True

    def webwxinit(self):
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
            self.pass_ticket, self.skey, int(time.time()))
        params = {
            'BaseRequest': self.base_request
        }
        dic = self._post(url, params)

        if dic == '':
            return False

        if 'ChatSet' in dic:
            contacts = dic['ChatSet'].split(',')
            self.group_ids = [group_id for group_id in contacts if '@@' in group_id]

        return dic['BaseResponse']['Ret'] == 0

    def webwxbatchgetcontact(self):
        url = self.base_uri + \
            '/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
                int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.base_request,
            "Count": len(self.group_ids),
            "List": [{"UserName": id, "EncryChatRoomId":""} for id in self.group_ids]
        }
        dic = self._post(url, params)

        if dic == '':
            return False

        self.groups = dic['ContactList']

        return True

    def _run(self, str, func, *args):
        print(str)
        if func(*args):
            print('succeed')
        else:
            print('failed\n[*] Exit the application')
            exit()

    def _get(self, url: object, timeout: object = None) -> object:
        request = urllib.request.Request(url=url)
        request.add_header('Referer', 'https://wx.qq.com/')
        try:
            response = urllib.request.urlopen(request, timeout=timeout) if timeout else urllib.request.urlopen(request)
            data = response.read().decode('utf-8')
            return data
        except urllib.error.HTTPError as e:
            logging.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logging.error('URLError = ' + str(e.reason))
        except http.client.HTTPException as e:
            logging.error('HTTPException')
        except timeout_error as e:
            pass
        except ssl.CertificateError as e:
            pass
        except Exception:
            import traceback
            logging.error('generic exception: ' + traceback.format_exc())
        return ''

    def _post(self, url: object, params: object, jsonfmt: object = True) -> object:
        if jsonfmt:
            data = (json.dumps(params)).encode()
            request = urllib.request.Request(url=url, data=data)
            request.add_header('ContentType', 'application/json; charset=UTF-8')
        else:
            request = urllib.request.Request(url=url, data=urllib.parse.urlencode(params).encode(encoding='utf-8'))

        try:
            response = urllib.request.urlopen(request)
            data = response.read()
            if jsonfmt:
                return json.loads(data.decode('utf-8') )
            return data
        except urllib.error.HTTPError as e:
            logging.error('HTTPError = ' + str(e.code))
        except urllib.error.URLError as e:
            logging.error('URLError = ' + str(e.reason))
        except http.client.HTTPException as e:
            logging.error('HTTPException')
        except Exception:
            import traceback
            logging.error('generic exception: ' + traceback.format_exc())
        return ''

    def findGroupMembers(self, group_name):
        while True:
            self.getUUID()
            self.genQRCode()
            print('[*] Please scan the QRCode to login to WeChat')
            if not self.waitForLogin():
                continue
                print('[*] Please confirm login on your phone... ')
            if not self.waitForLogin(0):
                continue
            break

        print('[*] Login WeChat')
        self.login()
        print('[*] WeChat Init')
        self.webwxinit()
        print('[*] Fetching WeChat Groups')
        self.webwxbatchgetcontact()
        for group in self.groups:
            if group['NickName'] == group_name:
                for member in group['MemberList']:
                    yield member
