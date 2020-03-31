__author__ = 'diansan'

from ..Basics import Basics
import os
import sys
import json
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
from lib.gvmanage_session import Basics
import time 

class Templates(Basics):
    def __init__(self, data, logger):
        super(Templates, self).__init__(data, logger)

    def create_cli_template(self, profile, expectation, template_name, template_desc, device_type, template_config,
                            config_type, factory_default):
        self.updateToken(profile)
        mount_point = '/template/device/cli/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'templateName': template_name,
                   'templateDescription': template_desc,
                   'deviceType': device_type,
                   'templateConfiguration': template_config,
                   'configType': config_type,
                   'factoryDefault': factory_default,
                   }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def get_template(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/template/device/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def get_task_status(self, profile, task_id):
        self.updateToken(profile)
        mount_point = '/device/action/status/%s' % task_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None,expectation = None)

    def get_feature_templates(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/template/feature'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def delete_feature_templates(self, profile, expectation,template_id):
        self.updateToken(profile)
        mount_point = '/template/feature/{}'.format(template_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)


    def get_devices_attached(self, profile, expectation,template_id):
        self.updateToken(profile)
        mount_point = '/template/device/config/attached/%s' % template_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)

    def attach_devices_to_template(self, profile, expectation, template_id, device_uuids, is_edited, is_master_edited):
        # Device Ids must be a list eg:['3ebc9345-a369-4201-902e-5eb0d136fe80']
        self.updateToken(profile)
        mount_point = '/template/device/config/input/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'templateId': template_id,
                   'deviceIds': device_uuids,
                   'isEdited': is_edited,
                   'isMasterEdited': is_master_edited}
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def push_template(self, profile, expectation, template_id, device, is_edited):
        # Sample device list: [{
        #                       'csv-status':'complete',
        #                       'csv-deviceId':'3ebc9345-a369-4201-902e-5eb0d136fe80',
        #                       'csv-deviceIP':'169.254.10.2',
        #                       'csv-host-name':'vm135',
        #                       'csv-templateId':'d278309b-a73a-42c4-bb29-5cf50308aa5b',
        #                       'selected':'true'
        #                     }]
        self.updateToken(profile)
        mount_point = '/template/device/config/attachcli'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'deviceTemplateList': [
            {'templateId': template_id, 'device': device, 'isEdited': is_edited}]}
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def delete_template(self, profile, expectation, template_id):
        # Device Ids must be a list eg:['3ebc9345-a369-4201-902e-5eb0d136fe80']
        self.updateToken(profile)
        mount_point = '/template/device/{}'.format(template_id)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {}
        return self.http_request(profile, 'DELETE', url, headers, json.dumps(payload), expectation=expectation)

    def detach_template(self, profile, expectation, deviceType, deviceIp, deviceId):
        # Device Ids must be a list eg:['3ebc9345-a369-4201-902e-5eb0d136fe80']
        self.updateToken(profile)
        mount_point = '/template/config/device/mode/cli'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'deviceType': deviceType, "devices": [
            {"deviceId": deviceId, "deviceIP": deviceIp}]}
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def get_all_available_devices_for_template(self, profile, expectation,templateId, chassis_id=False):
        mount_point = "/template/device/config/available/" + templateId
        devicesList = []
        devicesIdList = []
        #result = self.get_request(mount_point)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        result = self.http_request(profile, 'GET', url, headers, None, expectation=expectation)
        try:
            result = json.loads(result.content)['data']
        except KeyError:
            print "No devices available for template"
        else:
            for device in result:
                if chassis_id is True:
                    devicesList.append(device['uuid'])
                else:
                    devicesList.append(device['host-name'])
            return devicesList

    def get_template_content(self,profile, expectation, template_id):
        self.updateToken(profile)
        mount_point = '/template/device/object/%s'%template_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation=expectation)
        if res != {}:
            return res
        else:
            return ""

    def wait_for_push_task_to_complete(self, profile, expectation, task_id,
                                       wait_time=None, status="Success"):
        """
        Keeps polling until the template device action is done
        @param vmanage_hostname:
        @param mount_point_key:
        @return: list of the status
        """
        if wait_time:
            time.sleep(wait_time)

        result = self.get_task_status(profile, task_id)
        timeout = time.time() * 60
        statusList = []

        while result.json()['validation']['status'] == 'In progress':
            # keep polling until the validation task is done
            time.sleep(10)
            result = self.get_task_status(profile, task_id)
        if result.json()['validation']['status'] != 'Failure':
            while 'In progress' in result.json()['summary']['count'].keys() or\
                  'Scheduled' in result.json()['summary']['count'].keys():
                self.logger.debug('Sleeping for 30 seconds.')
                time.sleep(30)
                result = self.get_task_status(profile, task_id)
            tasksDict = result.json()['data']
            for action in tasksDict:
                if action['status'] == status:
                    statusList.append(True)
                else:
                    statusList.append(False)
            return statusList
        else:
            return [False]

    def edit_cli_template(self, profile, expectation, template_name, template_id, template_desc, device_type,
                          template_config,config_type, factory_default):
        self.updateToken(profile)
        mount_point = '/template/device/' + template_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {'templateId':template_id,'templateName': template_name,
                   'templateDescription': template_desc,
                   'deviceType': device_type,
                   'templateConfiguration': template_config,
                   'configType': config_type,
                   'factoryDefault': factory_default}
                   
        return self.http_request(profile, 'PUT', url, headers, json.dumps(payload), expectation=expectation)

    def create_Feature_template(self, profile, expectation, template_name, template_desc,  template_type, device_type, templateMinVersion,
                            templateDefinition, factory_default):
        self.updateToken(profile)
        mount_point = 'template/feature/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "templateName"          :   template_name,
                    "templateDescription"   :   template_desc,
                    "templateType"          :   template_type,
                    "deviceType"            :   device_type,
                    "templateMinVersion"    :   templateMinVersion,
                    "templateDefinition"    :   templateDefinition,
                    "factoryDefault"        :   factory_default

                   }
        
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def Edit_Feature_templates(self, profile, expectation, template_name, template_desc,  template_type, device_type, templateMinVersion,
                            templateDefinition, factory_default, template_id):
        self.updateToken(profile)
        mount_point = 'template/feature/'+ template_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "templateName"          :   template_name,
                    "templateDescription"   :   template_desc,
                    "templateType"          :   template_type,
                    "deviceType"            :   device_type,
                    "templateMinVersion"    :   templateMinVersion,
                    "templateDefinition"    :   templateDefinition,
                    "factoryDefault"        :   factory_default

                   }
        
        return self.http_request(profile, 'PUT', url, headers, json.dumps(payload), expectation=expectation)

    
    def create_device_template(self, profile, expectation, template_name, template_desc, device_type, generalTemplates):
        self.updateToken(profile)
        mount_point = '/template/device/feature/'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                        "templateName"              :   template_name,
                        "templateDescription"       :   template_desc,
                        "deviceType"                :   device_type,
                        "configType"                :   "template",
                        "factoryDefault"            :   "false",
                        "policyId"                  :   "",
                        "featureTemplateUidRange"   :   [],
                        "connectionPreferenceRequired": "true",
                        "connectionPreference"      :   "true",
                        "generalTemplates"          :   generalTemplates
                   }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)

    def edit_device_template(self, profile, expectation, template_id, template_name,  template_desc, device_type,
                          generalTemplates,securityPolicyId,localizedPolicyId):
        self.updateToken(profile)
        mount_point = '/template/device/' + template_id
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = { 'templateId'          : template_id,
                    'templateName'        : template_name,
                    'templateDescription' : template_desc,
                    'deviceType'          : device_type,
                    'configType'          : "template",
                    'factoryDefault'      : "false",
                    'policyId'            : "",
                    'featureTemplateUidRange': [],
                    'connectionPreferenceRequired': "true",
                    'connectionPreference': "true",
                    "generalTemplates"          :   generalTemplates
                   }
        if securityPolicyId != '':
            payload['securityPolicyId'] =  str(securityPolicyId)
        if localizedPolicyId != '':
            payload['policyId'] =  str(localizedPolicyId)
        return self.http_request(profile, 'PUT', url, headers, json.dumps(payload), expectation=expectation)


    def verify_dup_ip(self, profile, expectation, system_ip,uuid,device):
        self.updateToken(profile)
        mount_point = 'template/device/config/duplicateip'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                       "device":[
                           {
                                "csv-deviceIP":system_ip,
                                "csv-deviceId":uuid,
                                "csv-host-name":device
                            }  ]
                   }
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)


    def attach_feature_template(self, profile, expectation, template_id, device):
        self.updateToken(profile)
        mount_point = 'template/device/config/attachfeature'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name,
                   'Content-Type': 'application/json'}
        payload = {
                    "deviceTemplateList":[
                        {
                            "templateId"    :   template_id,
                            "device"        :   device,
                            "isEdited"      :   "true",
                            "isMasterEdited":   "false"
                        }
                                         ]
                    }
        print(json.dumps(payload))
        print(url)
        return self.http_request(profile, 'POST', url, headers, json.dumps(payload), expectation=expectation)
