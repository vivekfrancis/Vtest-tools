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
        print(url)
        print(payload)
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


    def create_TLSSSLPolicy(self, profile, expectation, sequence):
        self.updateToken(profile)
        a = True
        mount_point = 'template/policy/definition/ssldecryption'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type'   : 'application/json'}
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
                                                        "caCertBundle":{
                                                            "default": a
                                                        },
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
                                                "type":"drop"
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
