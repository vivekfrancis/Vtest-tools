__author__ = 'diansan'

import requests
import logging

from components import Host

from misc.Dashboard import Dashboard
from misc.Misc import Misc

from category import Monitor, Configuration, Tools, Maintenance, Administration, VAnalytics
from profile import ProviderProfile, TenantProfile, ProviderTenantProfile, SingleTenantProfile

# <dict> data:
#     <Key-str>'vm12':
#   ___________________
#  |                  |
#  |                  V
#  |      <Val-Host> obj {
#  |          <str>    name = 'vm12'
#  |          <str>    ip = '10.0.1.32'
#  |          <Domain> provider_domain = domain_obj
#  |          <Host>   next_synced_host = host_obj ________________________________________________
#  |                                                                                              |
#  |          <dict>   domains:                                                                   |
#  |              <Key-str> 'mtttest.viptela.com':                                                |
#  |                  <Val-Domain> obj {                                                          |
#  |                      <boolean> _is_provider = True                                           |
#  |                      <dict>    users:                                                        |
#  |                          <Key-str> 'admin':                                                  |
#  |                               <Val-User> obj{                                                |
#  |                                  <str>     name = 'admin'                                    |
#  |                                  <str>     password = 'admin'                                |
#  |                                  <Session> session = session_obj                             |
#  |                                  <dict>    tenants:                                          |
#  |                                      <Key-str>'apple': <Val-dict> apple_dict_obj             |
#  |                              }                                                               |
#  |                  }                                                                           |
#  |                                                                                              |
#  |              <Key-str> 'mtttest.apple.com':                                                  |
#  |                  <Val-Domain> obj {                                                          |
#  |                      <boolean> _is_provider = False                                          |
#  |                      <dict>    users:                                                        |
#  |                          <Key-str> 'tenantadmin':                                            |
#  |                              <Val-User> obj {                                                |
#  |                                  <str>     name = 'tenantadmin'                              |
#  |                                  <str>     password = 'tenantadmin'                          |
#  |                                  <Session> session = sessionObj                              |
#  |                              }                                                               |
#  |                                                                                              |
#  |                  }                                                                           |
#  |                                                                                              |
#  |  <Key-str>'vm18':                                                                            |
#  |                  ____________________________________________________________________________|
#  |                 |
#  |                 |
#  |                 V
#  |      <Val-Host> obj {
#  |          <str>    name = 'vm18'
#  |          <str>    ip = '10.0.1.38'
#  |          <Domain> provider_domain = domain_obj
#  |          <Host>   next_synced_host = host_obj __
#  |_________________________________________________|
#             <dict>   domains:
#                 <Key-str> 'mtttest.viptela.com':
#                     <Val-Domain> obj {
#                         <str>     name = 'mtttest.viptela.com'
#                         <boolean> _is_provider = True
#                         <dict>    users:
#                             <Key-str> 'admin':
#                                 <Val-User> obj{
#                                     <str>     name = 'admin'
#                                     <str>     password = 'admin'
#                                     <Session> session = sessionObj
#                                     <dict>    tenants:
#                                         <Key-str>'apple': <Val-dict> apple_dict_obj
#                                 }
#                     }
#
#                 <Key-str> 'mtttest.apple.com':
#                     <Val-Domain> obj {
#                         <boolean> _is_provider = False
#                         <dict>    users:
#                             <Key-str> 'tenantadmin':
#                                 <Val-User> obj {
#                                     <str>     name = 'tenantadmin'
#                                     <str>     password = 'tenantadmin'
#                                     <Session> session = sessionObj
#                                 }
#
#                     }
# }


class User(object):
    def __init__(self, username, password):
        self.name = username
        self.password = password
        self.session = requests.session()
        self.token = ''


class ProviderUser(User):
    def __init__(self, username, password):
        super(ProviderUser, self).__init__(username, password)
        self.tenants = {}

    def set_tenants(self, tenants):
        self.tenants = tenants


class Domain(object):
    def __init__(self, is_provider_domain, domain_name):
        self.name = domain_name
        self._is_provider_domain = is_provider_domain
        self.users = {}

    def _check_username_existence(self, username, does_expect_to_exist):
        if username in self.users and not does_expect_to_exist:
            raise Exception(
                'The username: %s already exists under domain: %s' % (username, self.name))
        if username not in self.users and does_expect_to_exist:
            raise Exception(
                'The username: %s doesn\'t exists under domain: %s' % (username, self.name))

    def register_user(self, username, password):
        try:
            self._check_username_existence(username, False)
        except Exception as e:
            raise e
        if self.is_provider_domain():
            self.users[username] = ProviderUser(username, password)
        else:
            self.users[username] = User(username, password)

    def unregister_user(self, username):
        try:
            self._check_username_existence(username, True)
        except Exception as e:
            raise e
        self.users.pop(username, None)

    def is_provider_domain(self):
        return self._is_provider_domain


class Host(object):
    def __init__(self, vmanage_hostname, vmanage_ip, default_domain_name):
        self.name = vmanage_hostname
        self.ip = vmanage_ip
        self.provider_domain = None
        self.domains = {}
        self.register_domain(False, default_domain_name)
        self.next_synced_host = self

    def _check_domain_name_existence(self, domain_name, does_expect_to_exist):
        if domain_name in self.domains and not does_expect_to_exist:
            raise Exception('The domain: %s already exists in self.domains: %s' % (
                domain_name, self.domains.keys()))
        if domain_name not in self.domains and does_expect_to_exist:
            raise Exception('The domain: %s doesn\'t exist in self.domains: %s' % (
                domain_name, self.domains.keys()))

    def register_domain(self, is_provider_domain, domain_name):
        try:
            self._check_domain_name_existence(domain_name, False)
        except Exception as e:
            raise e
        if self.provider_domain is not None and is_provider_domain:
            raise Exception('Only one provider is allowed per vManage! A provider domain: %s already registered on'
                            'vmanage: %s' % (domain_name, self.name))
        domain = Domain(is_provider_domain, domain_name)
        self.domains[domain_name] = domain
        if is_provider_domain:
            self.provider_domain = domain

    def unregister_domain(self, domain_name):
        try:
            self._check_domain_name_existence(domain_name, True)
        except Exception as e:
            raise e
        self.domains.pop(domain_name, None)

class VManageSession(object):
    def __init__(self, vmanages_info, provider_domain_name, logger = None):
        #Disable warning for insecure mode
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        if logger is None:
            logger = logging.getLogger('VManageSession logger')
        self.data = {}
        self.monitor = Monitor(self.data, logger)
        self.config = Configuration(self.data, logger)
        self.tools = Tools(self.data, logger)
        self.maint = Maintenance(self.data, logger)
        self.admin = Administration(self.data, logger)
        self.vanalytcs = VAnalytics(self.data, logger)
        self.dashboard = Dashboard(self.data, logger)
        self.misc = Misc(self.data, logger)
        self.token = ''
        self.session = {}  
                 
        
        for vmanage_name, info in vmanages_info.items():
            ip = info['mgmt_ip']
            domain_name = info['domain_name']
            username = info['username']
            password = info['password']
            host = Host(vmanage_name, ip, domain_name)
            host.domains[domain_name].register_user(username, password)
            self.data[vmanage_name] = host

            profile = self.create_provider_profile(vmanage_name, ip, username)
            response = self.misc.login(profile)
            if not response[0]:
                raise Exception(response[1])
            response = self.misc.get_all_tenants(profile, None)
            if response.status_code == requests.codes.FORBIDDEN:
                continue
            response = self.misc.get_tenancy_mode(profile, None)
            if response == 'SingleTenant':
                continue

            host.unregister_domain(domain_name)
            host.register_domain(True, provider_domain_name)
            host.domains[provider_domain_name].register_user(username, password)

            profile = self.create_provider_profile(vmanage_name, provider_domain_name, username)
            response = self.misc.login(profile)
            if not response[0]:
                raise Exception(response[1])
            for tenant in host.domains[provider_domain_name].users[username].tenants.values():
                tenant_domain = tenant['subDomain']
                host.register_domain(False, tenant_domain)
                host.domains[tenant_domain].register_user('tenantadmin', 'tenantadmin')
                tenant_profile = self.create_tenant_profile(vmanage_name, tenant_domain, 'tenantadmin')
                response = self.misc.login(tenant_profile)
                if not response[0]:
                    raise Exception(response[1])

        self.vmanage_ip = ip
        self.login(ip, username, password)
        

    def login(self, vmanage_ip, username, password):
        print "Username: %s " %username
        print "Password:%s " %password
        #base_url_str = 'https://%s:8443/'%vmanage_ip
        self.base_url_str = 'https://%s:8443/'%vmanage_ip

        login_action = '/j_security_check'
        headers = self.get_headers()
        headers.update({'Content-Type': 'application/x-www-form-urlencoded'})

        #Format data for loginForm
        login_data = {'j_username' : username, 'j_password' : password}

        #Url for posting login data
        login_url = self.base_url_str + login_action

        url = self.base_url_str + login_url

        sess = requests.session()

        response_login=sess.post(url=login_url, data=login_data, headers=headers, verify=False)

        self.session[vmanage_ip] = sess

        self.token = self.get_token()

    def get_headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['X-XSRF-TOKEN'] = self.token
        return headers

    def get_token(self):
        url = self.base_url_str + "dataservice/client/server"
        response = self.session[self.vmanage_ip].get(url=url, headers=None, verify=False)
        if not response.ok:
            return ''
        return response.json()['data'].get('CSRFToken', '')


    def sync_session_data_with_host(self, name_of_host_to_sync, names_of_hosts_to_be_synced):
        msg_q = ''
        synced_list_tail = self.data[name_of_host_to_sync]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head

        synced_hostname_set = set()
        while cur is not None:
            synced_hostname_set.add(cur.name)
            cur = cur.next_synced_host

        cur = synced_list_tail

        for hostname in set(names_of_hosts_to_be_synced) - synced_hostname_set:
            syncing_host = self.data[hostname]
            syncing_host.domains = {}
            syncing_host.provider_domain = None
            for domain in cur.domains.values():
                syncing_host.register_domain(domain.is_provider_domain(), domain.name)
                for user in domain.users.values():
                    syncing_host.domains[domain.name].register_user(user.name, user.password)
                    if domain.is_provider_domain():
                        profile = self.create_provider_profile(syncing_host.name, domain.name, user.name)
                    else:
                        profile = self.create_single_tenant_profile(syncing_host.name, domain.name, user.name)
                    res = self.misc.login(profile)
                    if not res[0]:
                        msg_q += res[1] + '\n'
            cur.next_synced_host = syncing_host
            cur = syncing_host
        cur.next_synced_host = synced_list_head
        return [len(msg_q) == 0, msg_q]

    # The vManage server side must have the domain before calling this function
    def register_domain(self, name_of_a_synced_host, is_provider_domain, domain_name):
        synced_list_tail = self.data[name_of_a_synced_host]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head
        cluster_host_list = []

        while cur is not None:
            cluster_host_list.append(cur.name)
            if not is_provider_domain and cur.provider_domain is not None:
                for user in cur.provider_domain.users.values():
                    provider_profile = self.create_provider_profile(cur.name, cur.provider_domain.name, user.name)
                    # if the session is already logged in then this call will update user's tenants info
                    self.misc.login(provider_profile)
            cur.register_domain(is_provider_domain, domain_name)
            cur = cur.next_synced_host

        synced_list_tail.next_synced_host = synced_list_head
        return [True, 'Successfully registered domain: %s among machines[%s]' % (domain_name, cluster_host_list)]

    # You should never unregister a provider's domain!
    # This function only applies to unregister non-provider domain
    def unregister_domain(self, vmanage_hostname, domain_name):
        synced_list_tail = self.data[vmanage_hostname]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head
        cluster_host_list = []

        if cur.provider_domain is not None:
            while cur is not None:
                for user in cur.provider_domain.users.values():
                    provider_profile = self.create_provider_profile(cur.name, cur.provider_domain.name, user.name)
                    # if the session is already logged in then this call will update user's tenants info
                    self.misc.login(provider_profile)
                cur.unregister_domain(domain_name)
                cur = cur.next_synced_host
        synced_list_tail.next_synced_host = synced_list_head
        return [True, 'Successfully unregistered domain: %s among machines: [%s]' % (domain_name, cluster_host_list)]

    def register_user(self, vmanage_hostname, domain_name, username, password):
        synced_list_tail = self.data[vmanage_hostname]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head
        cluster_host_list = []
        while cur is not None:
            cluster_host_list.append(cur.name)
            cur.domains[domain_name].register_user(username, password)
            cur = cur.next_synced_host
        synced_list_tail.next_synced_host = synced_list_head
        return [True, 'Successfully registered user: %s under domain: %s among machines: [%s]'
                % (username, domain_name, cluster_host_list)]

    def unregister_user(self, vmanage_hostname, domain_name, username):
        synced_list_tail = self.data[vmanage_hostname]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head
        cluster_host_list = []
        while cur is not None:
            cluster_host_list.append(cur.name)
            cur.domains[domain_name].unregister_user(username)
            cur = cur.next_synced_host
        synced_list_tail.next_synced_host = synced_list_head
        return [True, 'Successfully unregistered user: %s under domain: %s on machines: [%s]'
                % (username, domain_name, cluster_host_list)]

    def relogin_all_registered_sessions(self):
        ret = True
        err_msgs = ''
        for vmanage_hostname, vmanage_obj in self.data.items():
            if vmanage_obj.provider_domain is None:
                for domain_name, domain_obj in vmanage_obj.domains.items():
                    for username, user_obj in domain_obj.users.items():
                        profile = self.create_single_tenant_profile(vmanage_hostname, domain_name, username)
                        res = self.misc.login(profile)
                        if not res[0]:
                            ret = False
                            err_msgs += 'Failed to relogin vManage: %s with domain: %s as user: %s\n'\
                                        % (vmanage_hostname, domain_name, username)
            else:
                for domain_name, domain_obj in vmanage_obj.domains.items():
                    for username, user_obj in domain_obj.users.items():
                        if domain_obj.is_provider_domain():
                            profile = self.create_provider_profile(vmanage_hostname, domain_name, username)
                        else:
                            profile = self.create_tenant_profile(vmanage_hostname, domain_name, username)
                        res = self.misc.login(profile)
                        if not res[0]:
                            ret = False
                            err_msgs += 'Failed to relogin vManage: %s with domain: %s as user: %s\n'\
                                        % (vmanage_hostname, domain_name, username)
        return [ret, err_msgs]

    def is_cluster_ready(self, name_of_a_clustered_host, domain_name, username):
        synced_list_tail = self.data[name_of_a_clustered_host]
        synced_list_head = synced_list_tail.next_synced_host
        synced_list_tail.next_synced_host = None
        cur = synced_list_head
        cluster_hostname_list = []
        res = True
        msg = ''
        while cur is not None:
            cluster_hostname_list.append(cur.name)
            profile = self.create_provider_profile(cur.name, domain_name, username)
            response = self.admin.cluster_mgmt.get_cluster_server_status(profile, None)
            if isinstance(response, requests.ConnectionError):
                msg = str(response)
                break
            if response.status_code != 200:
                msg = 'response code = %s and doesn\'t match 200'
                break
            cur = cur.next_synced_host
        synced_list_tail.next_synced_host = synced_list_head
        if not res:
            return [res , msg]
        return [True, 'The cluster consists of [%s] is ready' % cluster_hostname_list]

    def create_single_tenant_profile(self, vmanage_hostname, vmanage_ip, username):
        return SingleTenantProfile(vmanage_hostname, vmanage_ip, username)

    def create_provider_profile(self, vmanage_hostname, domain_name, username):
        return ProviderProfile(vmanage_hostname, domain_name, username)

    def create_tenant_profile(self, vmanage_hostname, domain_name, username):
        return TenantProfile(vmanage_hostname, domain_name, username)

    def create_provider_tenant_profile(self, vmanage_hostname, domain_name, username, tenant_name):
        return ProviderTenantProfile(vmanage_hostname, domain_name, username, tenant_name)

    
