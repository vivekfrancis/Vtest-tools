__author__ = 'diansan'

import os
import re
import requests
import pdb
import json
from components import Validator
from profile import ProviderTenantProfile, ProviderProfile

STR_METHOD_NOT_ALLOWED_ERROR = '<html><head><title>Error</title></head><body>HTTP method POST is not supported by ' \
                               'this URL</body></html>'

class Basics(object):
    def __init__(self, data, logger):
        self.d = data
        self.logger = logger
        self._validator = Validator()


    def _send(self, profile, request_type, url, headers, payload, files):
        session = self.d[profile.vmanage_hostname].domains[profile.domain_name].users[profile.username].session
        self.logger.debug('URL                 ---> %s' % url)
        self.logger.debug('REQUEST_TYPE        ---> %s' % request_type)
        if isinstance(profile, ProviderTenantProfile):
            headers['VSessionId'] = self.d[profile.vmanage_hostname].domains[profile.domain_name].users\
                [profile.username].tenants[profile.tenant_name]['VSessionId']
            self.logger.debug('TENANT_NAME         ---> %s' % profile.tenant_name)
        self.logger.debug('HEADERS             ---> %s' % headers)
        self.logger.debug('PAYLOAD             ---> %s' % payload)

        try:
            if request_type == 'GET':
                res = session.get(url, headers = headers, data = payload, verify=False)
            elif request_type == 'PUT':
                res = session.put(url, headers = headers, data = payload, verify=False)
            elif request_type == 'POST':
                res = session.post(url, headers = headers, data = payload, files = files, verify=False)
            elif request_type == 'DELETE':
                res = session.delete(url, headers = headers, data = payload, verify=False)
            else:
                err_msg = 'The request type %s is not one of ["GET", "PUT", "POST", "DELETE"]' % request_type
                self.logger.error(err_msg)
                raise Exception(err_msg)
        except requests.ConnectionError as e:
            self.logger.error('Exception:          ---> %s\n\n\n!' % e)
            return e
        return res


    def _validate(self, response, expectation):
        if response.status_code != expectation['status_code']:
            err_msg = 'The status code of response: %s doesn\'t match expected: %s' %\
                      (response.status_code, expectation['status_code'])
            self.logger.error(err_msg + '\n\n\n')
            return [False, err_msg]

        if 'present' in expectation.keys():
            presence_err_msg = self._validator.checkPresenceDict(json.loads(json.dumps(expectation['present'])), response.json())
            # presence_err_msg = presence_dict_validation(json.loads(json.dumps(expectation['present'])), response.json())
            if len(presence_err_msg) != 0:
                err_msg = 'Present validation failed:\n%s' % presence_err_msg
                self.logger.error(err_msg + '\n\n\n')
                return [False, err_msg]

        if 'absent' in expectation.keys():
            absence_err_msg = self._validator.checkAbsenceDict(json.loads(json.dumps(expectation['absent'])), response.json())
            # absence_err_msg = absence_dict_validation(json.loads(json.dumps(expectation['absent'])), response.json())
            if len(absence_err_msg) != 0:
                err_msg = 'Absent validation failed:\n%s' % absence_err_msg
                self.logger.error(err_msg + '\n\n\n')
                return [False, err_msg]
        self.logger.debug('The call is successful!\n\n\n')
        return [True, response]

    def _generate_url(self, vmanage_hostname, mount_point, **kwargs):
        """Create url request for show command"""
        base_url = 'https://%s:8443' % self.d[vmanage_hostname].ip
        if mount_point[0] == '/': mount_point = mount_point[1:]
        if 'logout' in mount_point:
            url = os.path.join(base_url, mount_point)
        else:
            url = os.path.join(base_url, 'dataservice', mount_point)
        url += '?'
        for arg in kwargs:
            if kwargs[arg] is not None:
                url += '%s=%s&' % (re.sub('_', '-', arg), kwargs[arg])
        return url[0:-1]

    def _update_all_tenants_for_user(self, provider_profile):
        p = provider_profile
        url = self._generate_url(p.vmanage_hostname, '/tenant')
        res = self.http_request(p, 'GET', url, {'Host': p.domain_name}, None)
        tenant_list = []
        if 'data' in res.json():
            tenant_list = res.json()['data']
        self.d[p.vmanage_hostname].domains[p.domain_name].users[p.username].tenants = {}
        for tenant in tenant_list:
            url = self._generate_url(p.vmanage_hostname, '/tenant/%s/vsessionid' % tenant['tenantId'])
            res = self.http_request(p, 'POST', url, {'Host': p.domain_name}, None)
            tenant['VSessionId'] = res.json()['VSessionId']
            self.d[p.vmanage_hostname].domains[p.domain_name].users[p.username].tenants[tenant['name']] = tenant
        return [True, '']

    def _relogin(self, non_provider_tenant_profile):
        """Login to vmanage server and save cookies to cookie jar for future requests"""
        #Open login page to set and save initial cookies
        p = non_provider_tenant_profile
        password = self.d[p.vmanage_hostname].domains[p.domain_name].users[p.username].password
        url = 'https://%s:8443/j_security_check' % self.d[p.vmanage_hostname].ip
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'Host': p.domain_name}
        payload = {'j_username' : p.username, 'j_password' : password, 'submit': 'Log In'}

        session = self.d[p.vmanage_hostname].domains[p.domain_name].users[p.username].session
        self.logger.debug('Relogin... ')
        self.logger.debug('URL                 ---> %s' % url)
        self.logger.debug('REQUEST_TYPE        ---> %s' % 'POST')
        self.logger.debug('HEADERS             ---> %s' % headers)
        self.logger.debug('PAYLOAD             ---> %s' % payload)

        response = session.post(url, headers = headers, data = payload, verify=False)

        if response.status_code == requests.codes.METHOD_NOT_ALLOWED and response.content == STR_METHOD_NOT_ALLOWED_ERROR:
            msg = 'Already logged in : %s as user: %s' % (p.vmanage_hostname, p.username)
            if self.d[p.vmanage_hostname].domains[p.domain_name].is_provider_domain():
                res = self._update_all_tenants_for_user(p)
            return [True, msg]

        if response.status_code == requests.codes.OK:
            if 'Content-Type' in response.headers and response.headers['Content-Type'] == 'text/html':
                msg = 'Relogin failed! For login %s, username: %s and password: %s are invalid.'\
                      % (p.vmanage_hostname, p.username, password)
                self.logger.error(msg)
                raise Exception('Relogin failed: %s' % msg)
            # if it is a successful provider's user login, update all tenant data for every login
            if self.d[p.vmanage_hostname].domains[p.domain_name].is_provider_domain():
                res = self._update_all_tenants_for_user(p)
            #TODO: check if res is valid or not
            return [True, 'Successfully login to vmanage %s with domain_name: %s as user: %s'
                    % (p.vmanage_hostname, p.domain_name, p.username)]

        msg = 'Relogin failed! Unexpected status code: %s' % response.status_code
        self.logger.error(msg)
        raise Exception(msg)


    def http_request (self,
                      profile,
                      request_type,
                      url,
                      headers,
                      payload,
                      files = None,
                      expectation = None,
                      has_relogin = False):
        p = profile
        res = self._send(p, request_type, url, headers, payload, files)
        if isinstance(res, requests.ConnectionError):
            return res
        self.logger.debug('RES.STATUS_CODE     ---> %s' % res.status_code)
        self.logger.debug('RES.COOKIES         ---> %s' % res.cookies)

        if res.status_code == requests.codes.FORBIDDEN:
            self.logger.debug('RES.CONTENT         ---> %s' % res.content)

        elif 'Content-Type' in res.headers:
            content_type = res.headers['Content-Type']
            self.logger.debug('RES.CONTENT-TYPE    ---> %s' % content_type)
            if 'application/json' in content_type:
                if 'data' in res.json():
                    formatted = json.dumps(res.json()['data'], sort_keys=True, indent = 4, separators = (',', ':'))
                    self.logger.debug('RES.JSON()["data"]  --->\n%s' % formatted)
                else:
                    self.logger.debug('RES.CONTENT         ---> %s' % res.content)
            elif 'text/html' in content_type:
                self.logger.debug('RES.CONTENT         ---> %s' % res.content)
            else:
                self.logger.error('Unexpected response content-type status! Show it to Diansan before proceed! Thanks!')
                self.logger.debug('RES.CONTENT         ---> %s' % res.content)

        if 'Content-Type' in res.headers and 'text/html' in res.headers['Content-Type'] and '/logout' not in url \
            and 'id="errorMessageBox"' in res.content:
            self.logger.warning('Session expired. Will relogin and resend the call...')
            self.d[p.vmanage_hostname].domains[p.domain_name].users[p.username].session = requests.session()

            try:
                if isinstance(p, ProviderTenantProfile):
                    self._relogin(ProviderProfile(p.vmanage_hostname, p.domain_name, p.username))
                else:
                    self._relogin(p)
                return self.http_request(p,
                                     request_type,
                                     url,
                                     headers,
                                     payload,
                                     files = files,
                                     expectation = expectation,
                                     has_relogin = True)
            except Exception as e:
                return e

        if expectation is not None and len(expectation) != 0:
            return self._validate(res, expectation)

        self.logger.debug('No expectation found! Skipping the validation.\n\n\n')
        return res

    def _parse_headers(self, response, key=None):
        """Parse the header and data response from the server in the 
        form of a dictionary, with the field key as the primary dict key"""
        rdata = {}
        header_fields = []
        if 'header' not in response:
            return  rdata

        if 'fields' not in response['header']:
            self.logger("no header fields found in the response")
            return rdata

        for item in response['header']['fields']:
            header_fields.append(item['property'])

        self.logger.debug('Header fields : %s' % (str(header_fields)))
        if not key:
            key = header_fields[0]
            self.logger.warning('No key provided for the table.')
        
        if 'data' in response:
            current_index = ""
            for item in response['data']:
                if item[key] not in rdata:
                    current_index = item[key]
                    rdata[current_index] = {}
                for f in header_fields:
                    if f in item:
                        rdata[current_index][f] = item[f]
        return rdata
    
    def _get_uuid(self, response, anchor_key=None, anchor_value=None, return_key=None):
        """Return the uuid of the response dictionary list or
           Return the value of return_key.
        The element in the list will be choosen based on the anchor key-value match.
        """
        if not anchor_key or not anchor_value:
            return None
        
        for item in response.keys():
            if anchor_key in response[item] and anchor_value:
                    if response[item][anchor_key] == anchor_value:
                        if return_key and return_key in response[item]:
                            return response[item][return_key]
            if 'uuid' in item:
                return response[item]['uuid']
            else:
                return item
        return None

