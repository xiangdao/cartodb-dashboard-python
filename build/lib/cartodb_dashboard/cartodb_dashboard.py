# -*- encoding: utf-8 -*-

import warnings
import urlparse
import urllib
import httplib2
import urllib2
import sys
import os

try:
    import json
except ImportError:
    import simplejson as json

IMPORT_URL = '%(protocol)s://%(user)s.%(domain)s/api/%(api_version)s/imports'
SESSION_URL = '%(protocol)s://%(user)s.%(domain)s/sessions/create'
TABLES_URL = '%(protocol)s://%(user)s.%(domain)s/api/%(api_version)s/tables'

class CartoDBDashboardException(Exception):
    pass


class  CartoDbDashboard:
    """
    this class contains methods for performing operations exposed by the CartoDB Dashboard.
    """

    def __init__(self, cartodb_domain, user, password, host='cartodb.com', protocol='https', api_version='v1'):
        self.import_url = IMPORT_URL % {'user': cartodb_domain, 'domain': host, 'protocol': protocol, 'api_version': api_version}
        self.session_url = SESSION_URL % {'user': cartodb_domain, 'domain': host, 'protocol': protocol}
        self.table_url= TABLES_URL % {'user': cartodb_domain, 'domain': host, 'protocol': protocol, 'api_version': api_version}
        self.client = httplib2.Http()
        self.session_user = user
        self.session_password = password

    def request_session_headers(self):
        body = {'email': self.session_user, 'password': self.session_password}
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        response, content = self.client.request(self.session_url, 'POST', headers=headers, body=urllib.urlencode(body))
        headers['Cookie'] = response['set-cookie']
        return headers

    def req(self,url,http_method="GET", http_headers={}, body=''):
        if http_method == "POST":
            resp, content = self.client.request(url, "POST", body=body, headers=http_headers)
        elif http_method == "PUT":
            resp, content = self.client.request(url, "PUT", body=body, headers=http_headers)
        else:
            resp, content = self.client.request(url, "GET", headers=http_headers)

        if resp['status'] == '200':
            return json.loads(content)
        elif resp['status'] == '400':
            print resp
            print content
            raise CartoDBDashboardException(json.loads(content)['error'])
        elif resp['status'] == '500':
            print resp
            print content
            raise CartoDBDashboardException('internal server error')

        return None

    def __import_data(self,file):
        sessionbody = {'email': self.session_user, 'password': self.session_password}
        sessionheaders = {'Content-type': 'application/x-www-form-urlencoded'}
        response, content = self.client.request(self.session_url, 'POST', headers=sessionheaders, body=urllib.urlencode(sessionbody))

        def encode (file_path, fields=[]):
                BOUNDARY = '----------boundary------'
                CRLF = '\r\n'
                body = []

                for key, value in fields:
                    body.extend(
                      ['--' + BOUNDARY,
                       'Content-Disposition: form-data; name="%s"' % key,
                       '',
                       value,
                       ])

                file_name = os.path.basename(file_path)
                f = open(file_path, 'rb')
                file_content = f.read()
                f.close()
                body.extend(
                  ['--' + BOUNDARY,
                   'Content-Disposition: form-data; name="file"; filename="%s"'
                   % file_name,
                   'Content-Type: application/octet-stream',
                   '',
                   file_content,
                   ])

                body.extend(['--' + BOUNDARY + '--', ''])
                return 'multipart/form-data; boundary=%s' % BOUNDARY, CRLF.join(body)

        content_type, body = encode(file)
        headers = { 'Content-Type': content_type }
        headers['Cookie'] = response['set-cookie']

        return self.req(self.import_url, 'POST', http_headers=headers, body=body)['item_queue_id']

    def __convert_data_type(self,column,datatype,table):
        headers = self.request_session_headers()
        body = {'name': column, 'type': datatype}
        url = self.table_url +'/'+table +'/columns/'+column
        return self.req(url, 'PUT', http_headers=headers, body=urllib.urlencode(body))

    def check_imports(self):
        headers = self.request_session_headers()
        return self.req(self.import_url,'GET', http_headers=headers)

    def check_import(self,importid):
        headers = self.request_session_headers()
        return self.req(self.import_url+'/'+str(importid),'GET', http_headers=headers)

    def convert_data_type(self, column, datatype, table):
        try:
            self.__convert_data_type(column,datatype,table)
            return 0
        except CartoDBDashboardException as e:
            print ("some error ocurred:", e)
            return 1

    def import_data(self, file):
        try:
            importid = self.__import_data(file)
            check = 0;
            while check==0:
                res = self.check_import(importid)
                if res['state'] == 'uploading' or res['state'] == 'importing':
                    continue
                elif res['state'] == 'complete':
                    check = 1
            
            return 0, res['table_name']
        except CartoDBDashboardException as e:
            print ("some error ocurred:", e)
            return 1









