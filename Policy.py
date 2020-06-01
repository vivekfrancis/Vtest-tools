__author__ = 'diansan'

from ..Basics import Basics
import os
import sys
import json
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
from lib.gvmanage_session import Basics

class Policy(Basics):
    def __init__(self, data, logger):
        super(Policy, self).__init__(data, logger)

    def get_custom_app(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/template/policy/customapp/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def create_dataPrefix(self, profile, expectation,dataprefixname,entries):
        self.updateToken(profile)
        mount_point = '/template/policy/list/dataprefix/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'name': dataprefixname,
                   'description': "Desc Not Required",
                   'type': "dataprefix",
                   'entries': entries,
                   }
        print(json.dumps(payload))
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_SiteList(self, profile, expectation,sitename,entries):
        self.updateToken(profile)
        mount_point = '/template/policy/list/site/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'name': sitename,
                   'description': "Desc Not Required",
                   'type': "site",
                   'listId': 'null',
                   'entries': entries,
                   }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
    
    def create_VPN_List(self, profile, expectation,vpnname,entries):
        self.updateToken(profile)
        mount_point = '/template/policy/list/vpn/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'name': vpnname,
                   'description': "Desc Not Required",
                   'type': "vpn",
                    'listId': 'null',
                   'entries': entries,
                   }
        print(json.dumps(payload))
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_sequence(self, profile, expectation,policyname,description,sequence):
        self.updateToken(profile)
        mount_point = '/template/policy/definition/data/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {'name'           : policyname,
                    'type'          : "data",
                    'description'   : description,
                    'defaultAction' : {'type': "accept"},
                    'sequences'     : sequence              
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def get_dataPrefixlist(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/dataprefixall/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def delete_dataPrefixlist(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/dataprefix/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        print(url)
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_VPNList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/vpn/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def delete_VPNList(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/vpn/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_SITEList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/site/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    
    def delete_SITEList(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/site/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_dataPolicyId(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/data'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def delete_dataPolicyId(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/data/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        print(url)
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)
    
    def delete_appRoute(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/approute/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        print(url)
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_appRoute(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/approute'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def createPolicy(self, profile, expectation,policyDefinition):
        self.updateToken(profile)
        mount_point = 'template/policy/vsmart/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'policyDescription' : "desc",
                    'policyType'        : "feature",
                    'policyName'        : "TestDatapolicy",
                    'isPolicyActivated' : 'false',
                    'policyDefinition'  : policyDefinition
                 } 
        print(json.dumps(payload))
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def get_policyId(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/vsmart/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def delete_policyId(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/vsmart/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_policyStatus(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/vsmart/connectivity/status'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def activate_policy(self,profile, expectation, policy_id):
        self.updateToken(profile)
        mount_point = '/template/policy/vsmart/activate/'\
                '{pid}?confirm=true'.format(pid=policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {
                 }    
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def deactivate_policy(self,profile, expectation, policy_id):
        self.updateToken(profile)
        mount_point = '/template/policy/vsmart/deactivate/'\
                '{pid}?confirm=true'.format(pid=policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {
                 }    
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    # def createPolicy(self, profile, expectation,policyDefinition):
    #     self.updateToken(profile)
    #     mount_point = 'template/policy/vsmart/'
    #     url = self._generate_url(profile.vmanage_hostname, mount_point)
    #     headers = {'Host': profile.domain_name,
    #                'Content-Type'   : 'application/json'}
    #     payload = {  
    #                 'policyDescription' : "desc",
    #                 'policyType'        : "feature",
    #                 'policyName'        : "TestDatapolicy",
    #                 'isPolicyActivated' : 'false',
    #                 'policyDefinition'  : policyDefinition
    #              } 
    #     return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
    
    def createControlPolicy(self, profile, expectation,sequences,match,actions):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/control'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'name'          : "TestControlPolicy",
                    'type'          : "control",
                    'description'   : "desc",
                    'defaultAction' : {'type': "reject"},
                    'sequences'     : sequences,
                    'match'         :  match,
                    'actions'       : actions
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

###### Security policy ##########
    
    def get_zoneBaseFW(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/zonebasedfw'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_Intrusion_prevention(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/intrusionprevention'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_URLF(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/urlfiltering'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_AMP(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/advancedMalwareProtection'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)
    
    def get_SSL(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/ssldecryption'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_Security_policy(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/security'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_whitelisturl(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlwhitelist'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_blacklisturl(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlblacklist'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def create_Intrusion_prevention(self, profile, expectation, targetVPNs):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/intrusionprevention'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'name'                :   "TestIPP",
                    'type'                :   "intrusionPrevention",
                    'description'         :   "Testing",
                    'definition'          :   {
                                                'signatureSet'       :   "security", 
                                                'inspectionMode'     :   "detection", 
                                                'signatureWhiteList' :   {}, 
                                                'logLevel'           :   "warning",
                                                'logging'            :   [],
                                                'targetVpns'         :   targetVPNs
                                              }
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
    
    def create_URLF_Policy(self, profile, expectation, targetVPNs,whiteListId,blackListId):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/urlfiltering'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'name'              :     "TestURLF",
                    'type'              :     "urlFiltering",
                    'description'       :     "",
                    'definition'        :     {
                                                'webCategoriesAction' :     "block",
                                                'webCategories'       :     ["abortion", "abused-drugs"],
                                                'webReputation'       :     "moderate-risk",
                                                'urlWhiteList'        :     { 'ref' : whiteListId},
                                                'urlBlackList'        :     { 'ref' : blackListId},
                                                'blockPageAction'     :     "text",
                                                'blockPageContents'   :     "Access to the requested page has been denied. Please contact your Network Administrator",
                                                'enableAlerts'        :     'false',
                                                'alerts'              :      [],
                                                'logging'             :      [],
                                                'targetVpns'          :   targetVPNs
                                                }
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
    

    def create_whitelist_url(self, profile, expectation, urlPattern,name):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlwhitelist'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                        'name'            :   name,
                        'description'     :   "Desc Not Required",
                        'type'            :   "urlwhitelist",
                        'entries'         :   [ {'pattern': urlPattern} ] 

                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_blacklist_url(self, profile, expectation, urlPattern,name):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlblacklist'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                        'name'            :   name,
                        'description'     :   "Desc Not Required",
                        'type'            :   "urlblacklist",
                        'entries'         :   [ {'pattern': urlPattern} ] 

                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_SecurityPolicy(self, profile, expectation,zbfw_defid,InrusionPrevId,URLFpolicyId,AMPpolicyId,TLSSSLpolicyId):
        self.updateToken(profile)
        mount_point = 'template/policy/security/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                        'policyDescription'     :    "desc",
                        'policyType'            :    "feature",
                        'policyName'            :    "secpolicy",
                        'policyUseCase'         :    "custom",
                        'isPolicyActivated'     :   'false',
                        'policyDefinition'      :   {
                                                    'assembly'       : [        {'definitionId': zbfw_defid, 'type': "zoneBasedFW"},
                                                                                {'definitionId': InrusionPrevId, 'type': "intrusionPrevention"},
                                                                                {'definitionId': URLFpolicyId, 'type': "urlFiltering"},
                                                                                {'definitionId': AMPpolicyId, 'type': "advancedMalwareProtection"},
                                                                                {'definitionId': TLSSSLpolicyId, 'type': "sslDecryption"}
                                                                       ],
                                                    
                                                    'settings'              :   {'failureMode': "open"}
                                                    }
                        
                 }
        
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_AMP(self, profile, expectation, targetVPNs):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/advancedMalwareProtection'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'name'                      :    "TestAMP",
                    'type'                      :    "advancedMalwareProtection",
                    'description'               :    "",
                    'definition'                :   {
                                                    'matchAllVpn'               :   'false',
                                                    'fileReputationCloudServer' :   "apjc",
                                                    'fileReputationEstServer'   :   "apjc",
                                                    'fileReputationAlert'       :   "info",
                                                    'fileAnalysisCloudServer'   :   "",
                                                    'fileAnalysisFileTypes'     :   [],
                                                    'fileAnalysisAlert'         :   "",
                                                    'targetVpns'                :   targetVPNs
                                                    }
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    
    # def create_TLSSSLPolicy(self, profile, expectation, sequence):
    #     self.updateToken(profile)
    #     a = True
    #     mount_point = 'template/policy/definition/ssldecryption'
    #     url = self._generate_url(profile.vmanage_hostname, mount_point)
    #     headers = {'Host': profile.domain_name,
    #                'Content-Type'   : 'application/json'}
    #     payload = {
    #                                             "name":"TestSSLdecriptions",
    #                                             "type":"sslDecryption",
    #                                             "description":"TLS/SSL Proxy Policy Definition",
    #                                             "definition":{
    #                                                 "defaultAction":{
    #                                                     "type":"doNotDecrypt"
    #                                                 },
    #                                                 "sequences":[
    #                                                     {
    #                                                         "sequenceId":1,
    #                                                         "sequenceName":"Testrule1",
    #                                                         "baseAction":"decrypt",
    #                                                         "sequenceType":"sslDecryption",
    #                                                         "match":{
    #                                                         "entries":[
    #                                                             {
    #                                                                 "field":"sourceVpn",
    #                                                                 "value":"1"
    #                                                             }
    #                                                         ]
    #                                                         }
    #                                                     }
    #                                                 ],
    #                                                 "profiles":[

    #                                                 ],
    #                                                 "settings":{
    #                                                     "sslEnable":"true",
    #                                                     "expiredCertificate":"drop",
    #                                                     "untrustedCertificate":"drop",
    #                                                     "certificateRevocationStatus":"none",
    #                                                     "unknownStatus":"drop",
    #                                                     "unsupportedProtocolVersions":"drop",
    #                                                     "unsupportedCipherSuites":"drop",
    #                                                     "failureMode":"close",
    #                                                     "caCertBundle":{
    #                                                         "default": a
    #                                                     },
    #                                                     "keyModulus":"2048",
    #                                                     "eckeyType":"P256",
    #                                                     "certificateLifetime":1,
    #                                                     "minTlsVer":"TLSv1",
    #                                                     "caTpLabel":"PROXY-SIGNING-CA"
    #                                                 }
    #                                             }
    #                                             }
    #     return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_TLSSSLPolicy(self, profile, expectation, sequence):
        self.updateToken(profile)
        a = True
        mount_point = 'template/policy/definition/ssldecryption'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        caCertBundle = {
                           "default": False,
                           "fileName": 'myCA.pem',
                           "bundleString": "-----BEGIN CERTIFICATE-----\n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\nVg==\n-----END CERTIFICATE-----\n-----BEGIN CERTIFICATE-----\n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\nZA==\n-----END CERTIFICATE-----\n\n-----BEGIN CERTIFICATE-----\nMIIFgjCCA2qgAwIBAgIUbgmrDN1+dsoHDV2ew+2w9D7RbOEwDQYJKoZIhvcNAQEL\nBQAwcjEQMA4GA1UEAwwHUk9PVF9DQTETMBEGA1UECAwKQ2FsaWZvcm5pYTELMAkG\nA1UEBhMCVVMxHTAbBgkqhkiG9w0BCQEWDnJvb3RAY2lzY28uY29tMQ4wDAYDVQQK\nDAVDaXNjbzENMAsGA1UECwwEV0FBUzAeFw0yMDAxMDkwNzE3MzlaFw0yNTAxMDcw\nNzE3MzlaMHIxEDAOBgNVBAMMB1JPT1RfQ0ExEzARBgNVBAgMCkNhbGlmb3JuaWEx\nCzAJBgNVBAYTAlVTMR0wGwYJKoZIhvcNAQkBFg5yb290QGNpc2NvLmNvbTEOMAwG\nA1UECgwFQ2lzY28xDTALBgNVBAsMBFdBQVMwggIiMA0GCSqGSIb3DQEBAQUAA4IC\nDwAwggIKAoICAQDHdut7pgUWr0lZgXskPCFdmSECNqNT9vF1uSI5h9ccZa6kVCRy\nHkx0ZT5zYX16N0VtQk71i9HD2E9KGOOJDwU3DHTwpxf1oaWOXdyrNNaLaGKH8lNx\nE+6lQ4vQKj9FgFpQXR9lJ50zkPhEt8q9dpuC/Wtr3Cf1HFXQYExJd/RrZrTsacmN\ntab6oYBn7A0Gn9ShBYJLkE9TQ55yoJ1752NrUFG4KlTgWMq43jjzRyC1SnSLWdiF\npZEiA0eFs3RsGlR59NI/noROjge/EMU3Ocvjl38Kf4TiJfj0px5a2nXsCxvboe4x\njASjytbTtE4qPCwzlmKzg6+epZ3X9ILR9bLvi3fPBQhji/2aDP+mV7V8EHu68aSg\nddoOEGcHOhWXuKv26rt3SaGGJGEch6jsOGCR2HAEO/lEXxjxKCzUUplT+gKeCD1y\nBhTb501WSGJd0OC9+uHl83eyKRVhg6A7WdCxM34iCCESZjB+cSB76iWvnaSNJ4C3\npajC7kNf0b5yLi6GKbnLrCEc5cyPsWmlXhesBZq+8sUqQTZHccP9wGxcFgiBNMLE\nfIOm/f77jL6h7tUV4ncOq3E18girW0CZfRjmX1wZL/IZe3YI3NTSFxy4nCNOhww3\n7MaSqfwTuNmdXJGASlbd3+YK6+dfF+G2Mxwku4bLbb+kOe+y4R4EZzKEgQIDAQAB\noxAwDjAMBgNVHRMEBTADAQH/MA0GCSqGSIb3DQEBCwUAA4ICAQB8c9sTHcnK+Msh\nmtUqEneN0KWIjf/fqiE2X8B8RK9t5lJ/bb8bV9bHzgRllr0issF8fb6CIoVe5ydv\nbJUPzAzZA/usxJG3VugcoQmbTyRbokvOxiEhNXUbVYP2VtoR7vqZe7+JpIHRJ8Dv\nZIYvO5g7GwSLayGhPYb8u/H3lmBXcAtsTe+0HiDa742yrMht8uxDsjSGLw5q3yMN\n2iDRHbC2B4evYMIvQxhyRR1ZMCo4kY9ZA/dLr29hboK+WQCuPNIVSj1aCYHCE6Pc\nUqRN0IJz4viR+DvCc/YfnzHZf5bdYgonECbZl0uEpneV9GRJ+FhaRwdVkUHQlH31\nbJRFOQBVvrU15eDj/okU/rwHAj+XSN0GaQ04zYRAlQ+QDBDMuky4gfbw+JqBx4/R\ndFetjsVN1yeOKyaNzr5G/+SPNtio2DGJpEh9Ll59sdXmfelWr9F26c7L5U5gJ4Jk\nENQ4aLCmwrd9eXalfb5hUnKNBVtjh5n8Lkc0pUSxAYuHR6RmXu3vl+B93P/9A7Ny\nT01CnQhQx95cASPIkvrtojG/bHhk4a3vDfabGfExxq54GzWym6KExJmZOmkMhFmc\nTunXaFEST+SG0wiPCE8BGP5dVV4XObzC5h9VgfrZrDJGWhhciYv+6oTaktAuddSV\ndHjl4oJrfGXaHAOI6cUfP7Vk0DhFZg==\n-----END CERTIFICATE-----"
                       }
        payload = {
                                                "name":"TestSSLdecriptions",
                                                "type":"sslDecryption",
                                                "description":"TLS/SSL Proxy Policy Definition",
                                                "definition":{
                                                    "defaultAction":{
                                                        "type":"doNotDecrypt"
                                                    },
                                                    "sequences":[
                                                        {
                                                            "sequenceId":1,
                                                            "sequenceName":"Testrule1",
                                                            "baseAction":"decrypt",
                                                            "sequenceType":"sslDecryption",
                                                            "match":{
                                                            "entries":[
                                                                {
                                                                    "field":"sourceVpn",
                                                                    "value":"1"
                                                                }
                                                            ]
                                                            }
                                                        }
                                                    ],
                                                    "profiles":[

                                                    ],
                                                    "settings":{
                                                        "sslEnable":"true",
                                                        "expiredCertificate":"drop",
                                                        "untrustedCertificate":"drop",
                                                        "certificateRevocationStatus":"none",
                                                        "unknownStatus":"drop",
                                                        "unsupportedProtocolVersions":"drop",
                                                        "unsupportedCipherSuites":"drop",
                                                        "failureMode":"close",
                                                        "caCertBundle":caCertBundle,
                                                        "keyModulus":"2048",
                                                        "eckeyType":"P256",
                                                        "certificateLifetime":1,
                                                        "minTlsVer":"TLSv1",
                                                        "caTpLabel":"PROXY-SIGNING-CA"
                                                    }
                                                }
                                                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)


    def create_zbfw_policy(self, profile, expectation,srcNwRefId,destNwRefId,zoneListId):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/zonebasedfw'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                      "name":"zbfw",
                      "type":"zoneBasedFW",
                      "description":"zbfw",
                      "definition":{
                          "defaultAction":{
                              "type":"pass"

                  },
                          "sequences":[
                              {
                                  "sequenceId":1,
                                  "sequenceName":"Rule 1",
                                  "baseAction":"inspect",
                                  "sequenceType":"zoneBasedFW",
                                  "match":{
                                      "entries":[
                                          {
                                              "field":"sourceDataPrefixList",
                                              "ref": str(srcNwRefId)

                  },
                                          {
                                              "field":"destinationDataPrefixList",
                                              "ref":str(destNwRefId)

                  }

                  ]

                  },
                                  "actions":[ ]

                  }

                  ],
                          "entries":[
                              {
                                  "sourceZone": str(zoneListId),
                                  "destinationZone":str(zoneListId)

                  }

                  ]

                  }
                  }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def delete_Intrusionpolicy(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/intrusionprevention/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_URLFpolicy(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/urlfiltering/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_AMP(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/advancedMalwareProtection/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_TLSSSL(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/ssldecryption/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_securityPolicy(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/security/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_whitelistURL(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlwhitelist/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def delete_blacklistURL(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/urlblacklist/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

        
    def get_Lxc_install_status(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'client/activity/summary'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def PKI_config(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'sslproxy/settings/vmanage/rootca'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    
                    'commonName'    :    "Sdwan",
                    'org'           :    "Cisco",
                    'orgUnit'       :    "Cisco",
                    'locality'      :    "US",
                    'state'         :    "Newyork",
                    'country'       :    "US",
                    'validity'      :    10,
                    'email'         :    "test@cisco.com"
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)



    def createlocalizedPolicy(self, profile, expectation,definition):
        self.updateToken(profile)
        mount_point = 'template/policy/vedge/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                    'policyDescription'   :   "NbarAndFnF",
                    'policyType'          :   "feature",
                    'policyName'          :   "TestLocalizedPolicy",
                    'policyDefinition'    :   definition,
                    'isPolicyActivated'   :     'false'
                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def getlocalizedPolicy(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/vedge/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def deletelocalizedPolicy(self, profile, expectation,definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/vedge/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def createClass(self, profile, expectation,name,Type,queue):
        self.updateToken(profile)
        mount_point = '/template/policy/list/class'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "name"          :   name,
                    "description"   :   "Desc Not Required",
                    "type"          :   Type,
                    "entries"       :   [
                                        {
                                            "queue":queue
                                        }
                                        ]
                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
    
    
    def createACLPolicy(self, profile, expectation,name,desc,sequence):
        self.updateToken(profile)
        mount_point = '/template/policy/definition/acl'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "name"          :       name,
                    "type"          :       "acl",
                    "description"   :       name,
                    "defaultAction" :       {
                                                "type":"accept"
                                            },
                    "sequences"     :       sequence
                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def getClassList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/template/policy/list/class'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def getACLPolicy(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/template/policy/definition/acl'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def deleteACLPolicy(self, profile, expectation,policy_id):
        self.updateToken(profile)
        mount_point = '/template/policy/definition/acl/{}'.format(policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def deleteClassList(self, profile, expectation,policy_id):
        self.updateToken(profile)
        mount_point = '/template/policy/list/class/{}'.format(policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def createAppAwareRouting(self, profile, expectation,name,desc,sequence):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/approute'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    
                    "name"              :       name,
                    "type"              :       "appRoute",
                    "description"       :       desc,
                    "sequences"         :       sequence
                    
                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def getSLAClassList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/sla'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def createQOSPolicy(self, profile, expectation,name,desc,bandwidthPercent,bufferPercent,classMapRef):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/qosmap'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                   
                    "name"          :       name,
                    "type"          :       "qosMap",
                    "description"   :       desc,
                    "definition"    :       {
                                                "qosSchedulers":[
                                                                {
                                                                   "queue":"0",
                                                                    "bandwidthPercent":"85",
                                                                    "bufferPercent":"91",
                                                                    "burst":"15000",
                                                                    "scheduling":"llq",
                                                                    "drops":"tail-drop",
                                                                    "classMapRef":""
                                                                },
                                                               {
                                                                    "queue":"1",
                                                                    "bandwidthPercent":str(bandwidthPercent),
                                                                    "bufferPercent":str(bufferPercent),
                                                                    "scheduling":"wrr",
                                                                    "drops":"tail-drop",
                                                                    "classMapRef":str(classMapRef)
                                                                }
                                                                ]
                                            }
                 }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def getQOSMapList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/qosmap'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def deleteQOSMapList(self, profile, expectation,policy_id):
        self.updateToken(profile)
        mount_point = '/template/policy/definition/qosmap/{}'.format(policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def getHubAndSpokeId(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/hubandspoke'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def deleteHubAndSpoke(self, profile, expectation,policy_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/hubandspoke/{}'.format(policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def createHubAndSpoke(self, profile, expectation, name,desc,spokes,vpnListId,tlocid):
        self.updateToken(profile)
        a = True
        mount_point = 'template/policy/definition/hubandspoke'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                        "name"          :       name,
                        "type"          :       "hubAndSpoke",
                        "description"   :       desc,
                        "definition"    :       {
                                                    "vpnList": vpnListId,
                                                     "subDefinitions":[ 
                                                                         {
                                                                                "name":"My Hub-and-Spoke",
                                                                                "equalPreference":a,
                                                                                "advertiseTloc":a,
                                                                                "spokes": spokes,
                                                                                 "tlocList":tlocid
                                                                         }
                                                                      ]
                                                }
                    
                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def create_TLOCList(self, profile, expectation, TlocName, entries):
        self.updateToken(profile)
        mount_point = 'template/policy/list/tloc'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "name"          :       TlocName,
                    "description"   :       "Desc Not Required",
                    "type"          :       "tloc",
                    "entries"       :       entries
                }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def getTLOCList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/tloc'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def deleteTLOCList(self, profile, expectation,policy_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/tloc/{}'.format(policy_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)

    def get_ZoneList(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'template/policy/list/zone'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def create_zonelist(self, profile, expectation, entries):
        self.updateToken(profile)
        mount_point = 'template/policy/list/zone'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
        payload = {  
                       "name"           :"ZBFWList",
                        "description"   :"Desc Not Required",
                        "type"          :"zone",
                        "listId"        :None,
                        "entries"       :entries

                 } 
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def deleteZBFWList(self, profile, expectation,list_id):
        self.updateToken(profile)
        mount_point = 'template/policy/list/zone/{}'.format(list_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'DELETE', url, headers, None, expectation=expectation)
    
    def delete_Zbfw_policy(self, profile, expectation, definition_id):
        self.updateToken(profile)
        mount_point = 'template/policy/definition/zonebasedfw/{}'.format(definition_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
        'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

