# !/usr/bin/python

import confd_client
from tb_topology import TBTopology
import sys
import subprocess
import pdb
import json
import random
from new_runner import Runner
from args import Args
import os
from datetime import datetime
import xml.etree.ElementTree as ET
from itertools import islice
from time import sleep, time
import re
import time
import logging
import function_logger
import system_lib
import re
import paramiko, base64, socket
import pexpect
import script_ixload as ixL
import texttable
from texttable import Texttable
from profile import *
from copy import deepcopy
table = Texttable()
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
sys.path.insert(0, os.path.join(main_dir, 'vmanage'))
sys.path.insert(0, os.path.join(main_dir, 'suites'))
from lib.gvmanage_session.configuration.Templates import Templates
from lib.gvmanage_session import Basics
from lib.vmanage_session.VManageSession import VManageSession
from vmanage.scripts.vmanage_session import VmanageSession


args_obj = Args()
run = Runner(os.path.basename(__file__)[:-3], args_obj)

class appqoe_system(object):
    def __init__(self):
        args = args_obj.args
        from lib.multitenant_libs import config_helper
        from lib.args import Args
        self.topology = TBTopology(args)
        self.confd_client = confd_client.confd_client(None, '0.0.0.0', None, self.topology)
        self.config = self.topology.get_config()
        self.topo_tree = self.topology.topo_tree
        self.machines = self.config['machines']
        self.logger = logging.getLogger('runner')
        self.fn_logger = function_logger.FunctionLogger()
        self.confd_client.make_sure_all_sessions_are_up()
        self.run_name =  str(datetime.now()).split('.')[0].replace(" ", "_")

        global system
        system = system_lib.System(args, self.topology, self.confd_client)

        global vedges, pm_vedges, vsmarts, vmanages, vbonds, vm_vedges, cedges
        global kvm_vedges, esxi_vedges
        global vtest_tools_dir
        vedges = self.topology.match_personality_substring('vedge') +\
                 self.topology.match_personality_substring('cedge')
        pm_vedges = self.topology.pm_vedge_list()
        vsmarts = self.topology.vsmart_list()
        vbonds = self.topology.vbond_list()
        vmanages = self.topology.vmanage_list()
        vm_vedges = self.topology.vm_vedge_list()
        if len(vedges) != (len(pm_vedges) + len(vm_vedges)):
            diff_list = list(set(vedges) - set(pm_vedges) - set(vm_vedges))
            self.logger.error('Personality for Edge devices: %s do NOT match the pm/vm vedge_list as expected statically.'\
                              ' Please look at def pm_vedge_list and/or def vm_vedge_list in lib/tb_topology.py for a list of supported personalities.'\
                              ' Please make the changes in yaml or add the personality support in code and commit it !!' % diff_list)
            sys.exit(0)
        kvm_vedges = self.topology.match_personality_substring('kvm_vedge')
        cedges = self.topology.match_personality_substring('cedge')
        esxi_vedges = [m for m in vm_vedges if m not in kvm_vedges]
        vtest_tools_dir = os.path.expanduser('~') + '/vtest-tools/'

        self.set_globals()

    #---------------------------------------------------------------------------
    def set_globals(self):
        '''Set global variables for use in the script
        '''
        #------ Jumphost Details --------------
        global ubuntu_server, ubuntu_username
        ubuntu_server = self.topology.get_system_testbed_ip()
        ubuntu_username = self.topology.get_system_testbed_username()

        global profile, DEVICE_TYPE,vman_session,hostname
        try:
            if self.topology.match_personality_substring('vmanage'):
                vmanage = 'vm1001'
        except IndexError:
            pass
        if 'vmanage_session_config' in self.config and 'provider_domain_name' in self.config['vmanage_session_config']:
             vmanages_info = {}
             hostnames = self.topology.vmanage_list()
             for hostname in hostnames:
                 domain_ip = self.topology.get_ipaddr(hostname)
                 vmanages_info[hostname] = {
                     'mgmt_ip': domain_ip,
                     'domain_name': domain_ip,
                     'username': self.config['machines'][hostname]['gui_default_username'],
                     'password': self.config['machines'][hostname]['gui_default_password']
                 }

        hostname = hostnames[0]
        vman_session = VManageSession(vmanages_info, self.config['vmanage_session_config']['provider_domain_name'],	logger = self.logger)
        profile = vman_session.create_single_tenant_profile(hostname, vmanages_info[hostname]['mgmt_ip'] ,vmanages_info[hostname]['username'])

        global http
        http = VmanageSession(vmanages_info[hostname]['mgmt_ip'],hostname,logger = self.logger)

        global vManageIp
        vManageIp = vmanages_info[hostname]['mgmt_ip']

        DEVICE_TYPE = {}
        DEVICE_TYPE['pm9006']   = 'vedge-ASR-1002-HX'
        DEVICE_TYPE['pm9008']   = 'vedge-ASR-1002-HX'
        DEVICE_TYPE['pm9007']   = 'vedge-1000'
        DEVICE_TYPE['pm9011']   = 'vedge-2000'
        DEVICE_TYPE['pm9009']   = 'vedge-ISR-4351'
        DEVICE_TYPE['pm9010']   = 'vedge-ISR-4461'
        DEVICE_TYPE['pm9012']   = 'vedge-2000'


    #---------------------------------------------------------------------------
    #@run.test(['test_create_cli_templates_for_devices'])
    def test_create_cli_templates_for_devices(self,device):
            failcount = 0
            PushfailedDevices = []
            #Delete if any existing templates in loop
            # """Get template ids for deleting existing templates"""
            template_id = None
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
            for template in range(len(template_data)):
                if template_data[template]['templateName'] == device + '_Template':
                    template_id = template_data[template]['templateId']
                    delres = vman_session.config.tmpl.delete_template(profile,None,template_id)
                    if delres == 200:
                        self.logger.info('Able to delete existing templates successfully')
            #for device in pm_vedges:
            device_type = DEVICE_TYPE[device]
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            uuids = []
            uuids.append(uuid)
            if '/' in uuid:
                uuid = uuid.replace('/','%2F')
            res = vman_session.config.dev.get_device_running_config(profile,None,uuid)
            system_ip = self.topology.system_ip(device)
            config = self.get_config(res)
            # template_name = 'cli_template' + device
            # template_desc = 'cli_templatedesc' + device
            template_name = device + '_Template'
            template_desc = device + '_Template'
            """Create template for device"""
            return_status = vman_session.config.tmpl.create_cli_template(profile, None, template_name, template_desc,device_type, config, "file", "false")
            if int(return_status.status_code) != 200:
                return [False, 'Not able to create template for [%s]' % device_type]
            """Get template id"""
            template_id = None
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == template_name:
                        template_id = template['templateId']
            if template_id is None:
                return [False, 'no template {} found'.format(template_dict["name"])]
            res = vman_session.config.tmpl.attach_devices_to_template(profile, None, template_id, uuids,'false', 'false')
            if res.status_code != 200:
                return[False,'Not able to find available devices']
            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')
            devicedata = [{'csv-status':"complete",
                        'csv-deviceId': uuid,
                        'csv-deviceIP': system_ip,
                        'csv-host-name': device,
                        'csv-templateId': template_id,
                        'selected': "true"
                        }]
            push_response = vman_session.config.tmpl.push_template(profile, None, template_id,devicedata,'false')
            if push_response.status_code != 200:
                return[False,'Not able to attach template']
            processId = json.loads(push_response.content)['id']
            task_status = "Success"
            task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
            if task_status[0]:
                self.logger.info('Successfully created Cli template for [%s]' % device)
            else:
                failcount = failcount + 1
                self.logger.info('Failed to create Cli template for [%s]' % device)
                PushfailedDevices.append(device)

            if failcount == 0:
                return [True, 'Successfully created Cli template for all the devices']
            else:
                for device in PushfailedDevices:
                    self.logger.info('Failed to create Cli template for [%s]' % device)
                return [False, 'Not able to create template for all the devices']

    # @run.test(['test_create_cli_templates_for_vSmart'])
    def test_create_cli_templates_for_vSmart(self):
        failcount = 0
        PushfailedDevices = []
        for device in vsmarts:
            device_type = "vsmart"
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            res = vman_session.config.dev.get_device_running_config(profile,None,uuid)
            system_ip = self.topology.system_ip(device)
            config = self.get_config(res)
            # template_name = 'cli_template' + device
            # template_desc = 'cli_templatedesc' + device
            template_name = device + '_Template'
            template_desc = device + '_Template'
            """Create template for device"""

            return_status = vman_session.config.tmpl.create_cli_template(profile, None, template_name, template_desc,device_type, config, "file", "false")
            if int(return_status.status_code) != 200:
                return [False, 'Not able to create template for [%s]' % device_type]
            """Get template id"""
            template_id = None
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == template_name:
                        template_id = template['templateId']
            if template_id is None:
                return [False, 'no template {} found'.format(template_dict["name"])]
            uuids = []
            uuids.append(uuid)
            res = vman_session.config.tmpl.attach_devices_to_template(profile, None, template_id, uuids,'false', 'false')
            if res.status_code != 200:
                return[False,'Not able to find available devices']
            devicedata = [{'csv-status':"complete",
                        'csv-deviceId': uuid,
                        'csv-deviceIP': system_ip,
                        'csv-host-name': device,
                        'csv-templateId': template_id,
                        'selected': "true"
                        }]
            push_response = vman_session.config.tmpl.push_template(profile, None, template_id,devicedata,'false')
            if push_response.status_code != 200:
                return[False,'Not able to attach template']
            processId = json.loads(push_response.content)['id']
            task_status = "Success"
            task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
            if task_status[0]:
                self.logger.info('Successfully created Cli template for [%s]' % device)
            else:
                failcount = failcount + 1
                self.logger.info('Failed to create Cli template for [%s]' % device)
                PushfailedDevices.append(device)

        if failcount == 0:
            return [True, 'Successfully created Cli template for all the devices']
        else:
            for device in PushfailedDevices:
                self.logger.info('Failed to create Cli template for [%s]' % device)
            return [False, 'Not able to create template for all the devices']


    @run.test(['test_edit_cli_templates_Appqoe_configs','ISRVerify'])
    def test_edit_cli_templates_Appqoe_configs(self):
        failcount = 0
        PushfailedDevices = []
        pm_vedges = ['pm9009','pm9010']
        for device in pm_vedges:
            device_type = DEVICE_TYPE[device]
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            appqoeConfigsfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'appqoeConfigs.txt'))
            system_ip = self.topology.system_ip(device)
            with open(appqoeConfigsfile, "r") as file:
                appqoe_configs = file.read()
                file.close()
            """Get template id"""
            template_name = 'cli_template' + device
            template_desc = 'cli_templatedesc' + device
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == template_name:
                        template_id = template['templateId']
            if template_id is None:
                return [False, 'no template {} found'.format(template_dict["name"])]
            template_content_res = vman_session.config.tmpl.get_template_content(profile, None, template_id)
            if template_content_res.status_code != 200 :
                return [False, 'Failed to fetch template content']

            cedge_config = template_content_res.json()['templateConfiguration']
            with open(appqoeConfigsfile, "w") as f:
                f.write(cedge_config)
            with open(appqoeConfigsfile, "a") as f:
                f.write("\n")
                f.write(appqoe_configs)
                f.close()
            with open(appqoeConfigsfile, "r") as f2:
                lines = f2.readlines()
                f2.close()
            with open(appqoeConfigsfile, "w") as f:
                for line in lines:
                    if "controller-transactions" not in line:
                        f.write(line)
            with open(appqoeConfigsfile, "r") as f2:
                cedge_configs = f2.read()
                f2.close()
            edit_response = vman_session.config.tmpl.edit_cli_template(profile, None, template_name, template_id,
                                                               template_desc, device_type,cedge_configs, "file", False)
            if edit_response.status_code != 200:
                return[False,'Failed to edit cli template']
            uuids = []
            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')
            uuids.append(uuid)
            res = vman_session.config.tmpl.attach_devices_to_template(profile, None, template_id, uuids,'true', 'true')
            if res.status_code != 200:
                return[False,'Not able to find available devices']
            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')
            devicedata = [{'csv-status':"complete",
                        'csv-deviceId': uuid,
                        'csv-deviceIP': system_ip,
                        'csv-host-name': device,
                        'csv-templateId': template_id,
                        'selected': "true"
                        }]
            push_response = vman_session.config.tmpl.push_template(profile, None, template_id,devicedata,'true')
            if push_response.status_code != 200:
                return[False,'Not able to attach template']
            processId = json.loads(push_response.content)['id']
            task_status = "Success"
            task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
            if task_status[0]:
                self.logger.info('Successfully pushed appqoe configs to [%s]' % device)
            else:
                failcount = failcount + 1
                self.logger.info('Failed to push appqoe configs to [%s]' % device)
                PushfailedDevices.append(device)
        with open(appqoeConfigsfile, "w") as f:
                f.write(appqoe_configs)
                f.close()
        if failcount == 0:
            return [True, 'Successfully pushed appqoe configs to all the devices']
        else:
            for device in PushfailedDevices:
                self.logger.info('Failed to create Cli template for [%s]' % device)
            return [False, 'Failed to push appqoe configs to all the devices']


    def test_detach_templates_from_devices(self,devices):
        failcount = 0
        PushfailedDevices = []
        for device in devices:
            device_type = 'vedge'
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            system_ip = self.topology.system_ip(device)
            """Get template id"""
            template_name = device + '_Template'
            template_desc = device + '_Template'
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in range(len(template_data)):
                    if response.json()['data'][template]['templateName'] == template_name:
                        template_id = response.json()['data'][template]['templateId']
                        if template_id:
                            attachStatus = response.json()['data'][template]['devicesAttached']
                            if attachStatus != 0 :
                                res = vman_session.config.tmpl.detach_template(profile, None , device_type ,system_ip, uuid)
                                if res.status_code != 200:
                                    return[False,'Not able to detach device']
                                processId = json.loads(res.content)['id']
                                task_status = "Success"
                                task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
                                if task_status[0]:
                                    self.logger.info('Successfully detach device for [%s]' % device)
                                else:
                                    failcount = failcount + 1
                                    self.logger.info('Failed to detached template for [%s]' % device)
                                    PushfailedDevices.append(device)
                            else:
                                return [True, 'Device is in CLI mode']
        if failcount == 0:
            return [True, 'Successfully detached devices from templates']
        else:
            for device in PushfailedDevices:
                self.logger.info('Failed to detach Cli template for [%s]' % device)
            return [False, 'Not able to detach template for all the devices']


    #@run.test(['verifyHubSpoke'])
    def test_verifyHubSpoke(self):
            vpnIdList  = vman_session.config.policy.get_VPNList(profile, None)
            if vpnIdList.json()['data']:
                vpnReferenceId = vpnIdList.json()['data'][0]['listId']
            else:
                vpnname = 'vpn1'
                vpnentries = [{'vpn': "1"}]
                vpnRes = vman_session.config.policy.create_VPN_List(profile, None,vpnname,vpnentries)
                if vpnRes.status_code == 200:
                    vpnIdList  = vman_session.config.policy.get_VPNList(profile, None)
                    vpnReferenceId = vpnIdList.json()['data'][0]['listId']
            for device in pm_vedges:
                if self.config['machines'][device]['Hub'] == True:
                    systemIp    =   self.config['machines'][device]['system_ip']
                    sitename    =   "Hub"
                    siteentries =   [{'siteId': str(self.config['machines'][device]['site_id']) }]
                    siteRes     =   vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                    if siteRes.status_code != 200:
                        self.logger.info('Failed to create hub')

                    entries    =  []
                    TotalWANIntfs = self.config['machines'][device]['Total_wan_intfs']
                    for i in range(TotalWANIntfs):
                        color =  self.config['machines'][device]['interfaces']['TRANSPORT%s' %(i)]['color']
                        entries.append({
                                                "tloc"      :   str(systemIp),
                                                "color"     :   color,
                                                "encap"     :   "ipsec"
                                            })
                    tlocListRes     =   vman_session.config.policy.create_TLOCList(profile, None,'TLOCList', entries)
                    if tlocListRes.status_code == 200:
                        tlocid = json.loads(tlocListRes.content)['listId']


            SpokeList = []
            for device in pm_vedges:

                if self.config['machines'][device]['Spoke'] == True:
                    sitename    = "Spoke" + device
                    siteentries = [{'siteId': str(self.config['machines'][device]['site_id'])}]
                    siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                    if siteRes.status_code != 200:
                        self.logger.info('Failed to create spoke')
                    else:
                        spokeSitelistId = json.loads(siteRes.content)['listId']
                        SpokeList.append(spokeSitelistId)

            siteIdList = vman_session.config.policy.get_SITEList(profile, None)
            for i in range(len(siteIdList.json()['data'])):
                    if siteIdList.json()['data'][i]['name'] == 'Hub':
                        hubSiteRefId = siteIdList.json()['data'][i]['listId']

            hubs = [
                     {
                        "siteList": str(hubSiteRefId),
                        "prefixLists":[

                        ],
                        "ipv6PrefixLists":[

                        ]
                     }
                  ]
            spokes = []
            for i in range(len(SpokeList)):
                spokes.append({
                              "siteList" : str(SpokeList[i]),
                              "hubs" : hubs })

            res = vman_session.config.policy.createHubAndSpoke(profile, None,"HubAndSpoke","HubAndSpoke",spokes,vpnReferenceId,tlocid)
            if res.status_code == 200:
                return [True, 'Able to create HubSpokeTopology']
            else:
                return [False, 'Not able to create HubSpokeTopology']


    # @run.test(["test_deletedatapolicy"])
    def test_deletedatapolicy(self):
            flag = 0
            res = vman_session.config.policy.get_policyId(profile, None)
            vsmart_policy_name = 'TestDatapolicy'

            if res.json()['data']:
                    for policy in res.json()['data']:
                            if policy['policyName'] == vsmart_policy_name:
                                policyId = policy['policyId']
                                delres = vman_session.config.policy.delete_policyId(profile, None,policyId)
                                if delres.status_code != 200:
                                    flag = flag + 1
                                    return [False, 'unable to delete policy id']
                            else :
                                return [False, 'Unable to get policy']
            else:
                    self.logger.info('Not policy found with given name')

            dataPolicyId  = vman_session.config.policy.get_dataPolicyId(profile, None)
            if dataPolicyId.status_code == 200:
                    if dataPolicyId.json()['data']:
                        datapolicyRefId = dataPolicyId.json()['data'][0]['definitionId']
                        deletedataPolicy = vman_session.config.policy.delete_dataPolicyId(profile, None, datapolicyRefId)
                        if deletedataPolicy.status_code != 200:
                            flag = flag + 1

            deleteAppawarepolicy = self.test_delete_AppAwareRoutingPolicy()
            if deleteAppawarepolicy[0]:
                self.logger.info('deleted appaware policy')
            else:
                flag = flag + 1
                self.logger.info('Not able to delete appaware policy')

            deleteHubspoke = self.test_deleteHubSpoke()
            if deleteHubspoke[0]:
                self.logger.info('deleted hubspoke')
            else:
                flag = flag + 1
                self.logger.info('Not able to delete huspoke')

            siteIdList = vman_session.config.policy.get_SITEList(profile, None)
            if siteIdList.status_code == 200:
                    if siteIdList.json()['data']:
                        for i in range(len(siteIdList.json()['data'])):
                            siteReferenceId = siteIdList.json()['data'][i]['listId']
                            deleteSITEList = vman_session.config.policy.delete_SITEList(profile, None, siteReferenceId)
                            if deleteSITEList.status_code != 200:
                                flag = flag + 1

            vpnIdList  = vman_session.config.policy.get_VPNList(profile, None)
            if vpnIdList.status_code == 200:
                    if vpnIdList.json()['data']:
                        for i in range(len(vpnIdList.json()['data'])):
                            vpnReferenceId = vpnIdList.json()['data'][i]['listId']
                            deletevpnList = vman_session.config.policy.delete_VPNList(profile, None, vpnReferenceId)
                            if deletevpnList.status_code != 200:
                                flag = flag + 1

            getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
            if getdataPrefix.status_code != 200:
                flag = flag + 1

            else:
                if getdataPrefix.json()['data']:
                        for i in range(len(getdataPrefix.json()['data'])):
                                if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':

                                    srcNwRefId = getdataPrefix.json()['data'][i]['listId']
                                    deletedataPrefix = vman_session.config.policy.delete_dataPrefixlist(profile, None, srcNwRefId)

                                elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':

                                    destNwRefId = getdataPrefix.json()['data'][i]['listId']
                                    deletedataPrefix = vman_session.config.policy.delete_dataPrefixlist(profile, None, destNwRefId)

            if flag == 0:
                    return [True, 'Able to delet datapolicy']
            else:
                    return [False, 'Not able to delet datapolicy']

    def test_create_dataPrefix(self):
           flag = 0
           srcNwRefId = ''
           destNwRefId = ''
           getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
           if getdataPrefix.status_code != 200:
               self.logger.info('unable to get dataprefix list')

           else:
               for i in range(len(getdataPrefix.json()['data'])):
                    if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                        srcNwRefId = getdataPrefix.json()['data'][i]['listId']
                    elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                        destNwRefId = getdataPrefix.json()['data'][i]['listId']
           if srcNwRefId == '':

                dataprefixname = 'srcNetwork'
                dataprefixentries = [{'ipPrefix': "173.19.50.0/24"}]
                dataPrefixres = vman_session.config.policy.create_dataPrefix(profile, None,dataprefixname,dataprefixentries)
                if dataPrefixres.status_code != 200:
                    flag = flag + 1

           if destNwRefId == '':

                dataprefixname = 'destNetwork'
                dataprefixentries = [{'ipPrefix': "173.20.10.0/24"}]
                dataPrefixres = vman_session.config.policy.create_dataPrefix(profile, None,dataprefixname,dataprefixentries)
                if dataPrefixres.status_code != 200:
                    flag = flag + 1

           if flag == 0:
               return [True, 'Data prefix is created']
           else:
               return [False, 'Data prefix is not created']


    # @run.test(['createdatapolicy'])
    def test_create_tcpOpt_dataPolicy(self):
            dataPrefixres = vman_session.config.policy.get_custom_app(profile, None)
            createdataPrefix = self.test_create_dataPrefix()
            if createdataPrefix:
                self.logger.info('data prefix is created')
            else:
                self.logger.info('data prefix is not created')

            getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
            if getdataPrefix.status_code != 200:
                self.logger.info('unable to get dataprefix list')

            else:
                for i in range(len(getdataPrefix.json()['data'])):
                        if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                            srcNwRefId = getdataPrefix.json()['data'][i]['listId']
                        elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                            destNwRefId = getdataPrefix.json()['data'][i]['listId']

            for device in pm_vedges:
                    if self.config['machines'][device]['Datapolicy'] == True:
                        sitename    = "datapolicy_" + device
                        siteentries = [{'siteId': str(self.config['machines'][device]['site_id']) }]
                        siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                        if siteRes.status_code != 200:
                            self.logger.info('Failed to create sitelist')

                    if self.config['machines'][device]['AppAwareroutingpolicy'] == True:
                        sitename    = "AppAwareroutingpolicy_" + device
                        siteentries = [{'siteId': str(self.config['machines'][device]['site_id']) }]
                        siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                        if siteRes.status_code != 200:
                            self.logger.info('Failed to create sitelist')


            vpnname = 'vpn1'
            vpnValue = self.config['VPN']
            vpnentries = [{'vpn': vpnValue}]

            vpnRes = vman_session.config.policy.create_VPN_List(profile, None,vpnname,vpnentries)
            siteIdList = vman_session.config.policy.get_SITEList(profile, None)
            dataPolicysiteList = []
            AARSiteList = []
            for i in range(len(siteIdList.json()['data'])):
                    if 'datapolicy_' in siteIdList.json()['data'][i]['name']:
                        siteReferenceId = siteIdList.json()['data'][i]['listId']
                        dataPolicysiteList.append(siteReferenceId)
                    elif 'AppAwareroutingpolicy_' in siteIdList.json()['data'][i]['name']:
                        siteReferenceId = siteIdList.json()['data'][i]['listId']
                        AARSiteList.append(siteReferenceId)

            vpnIdList  = vman_session.config.policy.get_VPNList(profile, None)
            vpnReferenceId = vpnIdList.json()['data'][0]['listId']

            if self.config['ControlPolicy'] == True:
                    hubSpoke = self.test_verifyHubSpoke()
                    if hubSpoke:
                        self.logger.info('Created hubspoke successfully')
                        hubSpokeres = vman_session.config.policy.getHubAndSpokeId(profile, None)
                        if hubSpokeres.status_code == 200:
                            hubSpokeId = hubSpokeres.json()['data'][0]['definitionId']

                    else:
                        self.logger.info('Not able to create hubspoke')

            if self.config['AppawareRoutingPolicy'] == True:
                    appAwarePolicy = self.test_create_AppAwareRoutingPolicy()
                    if appAwarePolicy:
                        self.logger.info('Created App aware routing policy successfully')
                        res = vman_session.config.policy.get_appRoute(profile,None)
                        if res.status_code == 200:
                            aapAwarepolicyId = json.loads(res.content)['data'][0]['definitionId']
                    else:
                        self.logger.info('Not able to create Appaware routing policy')

            sequence2 = [{
                            'sequenceId'     : 1,
                            'sequenceName'   : "Custom",
                            'baseAction'     : "accept",
                            'sequenceType'   : "data",
                            'sequenceIpType' : "ipv4",
                            'match'          :  {'entries':
                                                [{'field': "sourceDataPrefixList", 'ref': srcNwRefId},
                                                {'field': "destinationDataPrefixList", 'ref': destNwRefId}
                                                ]
                                                },
                            'actions'        :  [
                                                {'type': "tcpOptimization", 'parameter': "null"}
                                                ]
                }
                ]
            if self.config['PacketDup'] == True:
                sequence2[0]['actions'].append(
                {
               "type":"lossProtect",
               "parameter":"packetDuplication"
                })
                sequence2[0]['actions'].append(
                {
               "type":"lossProtectPktDup",
               "parameter":"packetDuplication"
                })

            if self.config['FEC'] == True:
                sequence2[0]['actions'].append(
                {
               "type":"lossProtect",
               "parameter":"fecAlways"
                })
                sequence2[0]['actions'].append(
                {
               "type":"lossProtectFec",
               "parameter":"fecAlways"
                })

            sequenceresp = vman_session.config.policy.create_sequence(profile, None,'testdataPolicy','description',sequence2)
            dataPolicyId  = vman_session.config.policy.get_dataPolicyId(profile, None)
            datapolicyRefId = dataPolicyId.json()['data'][0]['definitionId']
            policyDefinition = {
                    'assembly'     : [{
                                            'definitionId' : datapolicyRefId,
                                            'type'         : "data",
                                            'entries'      :  [{
                                                                    'direction'   : "service",
                                                                    'siteLists'   : dataPolicysiteList,
                                                                    'vpnLists'    : [vpnReferenceId]
                                                                }]

                                        }]
                    }
            if self.config['ControlPolicy'] == True:
                policyDefinition['assembly'].append({'definitionId' : str(hubSpokeId), 'type' : "hubAndSpoke"})

            if self.config['AppawareRoutingPolicy'] == True:
                policyDefinition['assembly'].append(
                                                        {
                                                        'definitionId' : str(aapAwarepolicyId),
                                                        'type' : "appRoute",
                                                        'entries'      :  [{
                                                                    'direction'   : "service",
                                                                    'siteLists'   : AARSiteList,
                                                                    'vpnLists'    : [vpnReferenceId]
                                                                }]

                                                        }
                                                    )
            resp = vman_session.config.policy.createPolicy(profile, None,policyDefinition)
            if resp.status_code == 200:
                return [True, 'Datapolicy created successfully']
            else:
                return [False, 'Datapolicy is not created']


    #@run.test(['Activatedatapolicy'])
    def test_activate_tcpOpt_dataPolicy(self):
        res = vman_session.config.policy.get_policyId(profile, None)
        vsmart_policy_name = 'TestDatapolicy'
        for policy in res.json()['data']:
            if policy['policyName'] == vsmart_policy_name:
                policyId = policy['policyId']
        res = vman_session.config.policy.get_policyStatus(profile, None)
        if res.status_code != 200:
            return [False, 'vSmart template is not created properly']
        response = vman_session.config.policy.activate_policy(profile, None, policyId)
        if not response.ok:
            print 'some error:', response.text
            return 1
        processId = json.loads(response.content)['id']
        task_status = "Success"
        task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
        if task_status[0]:
            self.logger.info('Successfully activated datapolicy')
            return [True, 'Successfully activated datapolicy']
        else:
            self.logger.info('Not able to activate datapolicy')
            return [False, 'Not able to activate datapolicy']

    def test_deactivate_tcpOpt_dataPolicy(self):
        res = vman_session.config.policy.get_policyId(profile, None)
        vsmart_policy_name = 'TestDatapolicy'
        if json.loads(res.content)['data']:
            for i in range(len(json.loads(res.content)['data'])):
                if json.loads(res.content)['data'][i]['policyName'] == vsmart_policy_name:
                    policyId = json.loads(res.content)['data'][i]['policyId']
                    if json.loads(res.content)['data'][i]['isPolicyActivated'] != False:
                        response = vman_session.config.policy.deactivate_policy(profile, None, policyId)
                        if not response.ok:
                            print 'some error:', response.text
                            return 1
                        processId = json.loads(response.content)['id']
                        task_status = "Success"
                        task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
                        if task_status[0]:
                            self.logger.info('Successfully deactivated datapolicy')
                            return [True, 'Successfully deactivated datapolicy']
                        else:
                            self.logger.info('Not able to deactivate datapolicy')
                            return [False, 'Not able to deactivate datapolicy']
                    else:
                        self.logger.info('Policy is not attached to devic')
                        return [True, 'Policy is already deactivated']
                else:
                    self.logger.info('no policy found with given name')
        return [True, 'No policies found to deactivate']

    @run.test(['RebootDevices'])
    def RebootDevices(self):
        pm_vedges = ['pm9006','pm9008','pm9010']
        failcount = 0
        PushfailedDevices = []
        table_result = []
        for i in range(5):
            bfdSessionFlag = []
            ompSessionFlag = []
            attachFail     = []
            flag = 0
            ## Pre-requiste: Template should be created, without attaching to device
            for device in pm_vedges:

                ## Calling attach template proc ##
                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                table_result.append(['',''])
                self.logger.info('******** Template attach on iteration: **********:  {}'.format(i))

                if 'vedge_' in self.config['machines'][device]['personality']:
                    attachresult = self.test_create_cli_templates_for_devices(device)
                else:
                    attachresult = self.test_feature_template_Edit_Attach(device)
                if attachresult:
                    self.logger.info('******** Attach successfull on iteration: **********:  {}'.format(i))
                    table_result.append(['Test Attach Feature Template: ', 'PASS'])
                else:
                    self.logger.info('******** Attach failure on iteration: **********:  {}'.format(i))
                    table_result.append(['Test Attach Feature Template: ', 'FAIL'])
                    attachFail.append(device)
                    flag = flag + 1

                # self.logger.info('******** verify appqoe configs on iteration before reboot: **********:  {}'.format(i))
                # ###############Appqoe events###############
                # if self.config['machines'][device]['Securitypolicy'] == True:
                #     tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)
                #
                #     if tcp_opt_status[0]:
                #         self.logger.info('TCP opt status is running: ')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('TCP opt status is not running:')
                #     utdresult = self.test_verify_UTD_configs(device)
                #
                #     if utdresult[0]:
                #         self.logger.info('UTD is alive')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('utd is not configured')
                #
                #     trustpointstatus = self.test_verify_trustpoint_status(device)
                #
                #     if trustpointstatus[0]:
                #         self.logger.info('trustpoint is configured')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('trustpoint is not configured')
                #
                #     utdstatus = self.test_UTDStatus(device)
                #
                #     if utdstatus[0]:
                #         self.logger.info('utd is running')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('utd is not running')
                #
                # if self.config['machines'][device]['Appqoe'] == True:
                #     appqoeresult = self.test_verify_Appqoe_configs(device)
                #
                #     if appqoeresult[0]:
                #         self.logger.info('Appqoe is alive')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('Appqoe is not configured')

                uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
                system_ip = self.topology.system_ip(device)
                #Get bfd sessions output before reboot
                res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                if res.status_code == 200:
                    bfdSessionsUpbeforeReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                    self.logger.info('Bfd Sessions up before Reboot: [%s]' % bfdSessionsUpbeforeReboot)
                    table_result.append(['Test BFD Sessions up before Reboot: ', 'PASS'])
                else:
                    table_result.append(['Test BFD Sessions up before Reboot: ', 'FAIL'])
                    flag = flag + 1
                #Get omp peer check summary before reboot
                res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                if res.status_code == 200:
                    tlocSentbeforeReboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                    tlocRecievedbeforeReboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                    vSmartpeerbeforeReboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                    operStatebeforeReboot     =  json.loads(res.content)['data'][0]['operstate']
                    self.logger.info('tloc sent before Reboot: [%s]' % tlocSentbeforeReboot)
                    self.logger.info('tloc sent before Reboot: [%s]' % tlocRecievedbeforeReboot)
                    self.logger.info('tloc sent before Reboot: [%s]' % vSmartpeerbeforeReboot)
                    self.logger.info('tloc sent before Reboot: [%s]' % operStatebeforeReboot)
                    table_result.append(['Test OMP peer Sessions up before Reboot: ', 'PASS'])
                else:
                    table_result.append(['Test OMP peer Sessions up before Reboot: ', 'FAIL'])
                    flag = flag + 1
                devices = [
                    {
                        'deviceIP' : system_ip, 'deviceId' : uuid
                    }
                    ]

                res = vman_session.maint.dev_reboot.reboot_devices(profile, None,'reboot','vedge',devices)
                if res.status_code != 200:
                    self.logger.info('Not able to reboot device %s' % device)
                processId = json.loads(res.content)['id']
                res = vman_session.maint.dev_reboot.get_device_reboot_status(profile, None,processId)
                if res == 'False':
                    self.logger.info('Validation failure for device %s' % device)
                task_status = "Success"
                try:
                    task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, processId, 120, task_status)
                    if task_status[0]:
                        self.logger.info('Successfully rebooted device [%s]' % device)
                        self.logger.info('Successfully rebooted device on iteration: {}'.format(i))
                        table_result.append(['Test Reboot device: ', 'PASS'])
                    else:
                        failcount = failcount + 1
                        self.logger.info('Failed to reboot for [%s]' % device)
                        self.logger.info('Failed to reboot for iteration: {}'.format(i))
                        table_result.append(['Test Reboot device: ', 'FAIL'])
                        PushfailedDevices.append(device)
                        flag = flag + 1
                except:
                    pass
                    self.logger.info('Caught an exception on reboot for iteration: {}'.format(i))


                # if self.config['machines'][device]['Appqoe'] == True:
                #     appqoeresult = self.test_verify_Appqoe_configs(device)
                #
                #     if appqoeresult[0]:
                #         self.logger.info('Appqoe is alive')
                #     else:
                #         flag = flag + 1
                #         self.logger.info('Appqoe is not configured')

                #verify crash log details from device
                try:
                    crashlogres = vman_session.dashboard.device_crashlog(profile, None,system_ip)
                    if crashlogres.status_code == 200:
                        self.logger.info('Fetching crash details from device')
                        data = json.loads(crashlogres.content)['data']
                        if not data:
                            self.logger.info('Crash is not seen for device [%s]' % device)
                            table_result.append(['Test Check Crash logs: ', 'PASS'])
                        else:
                            table_result.append(['Test Check Crash logs: ', 'FAIL'])
                            self.logger.info(' ******** Crash found ********** ')
                            self.logger.info('Crash found for device [%s]' % device)
                            flag = flag + 1
                            for eachcrash in data :
                                self.logger.info('core time :', eachcrash['core-time'])
                                self.logger.info('core filename :', eachcrash['core-filename'])
                                self.logger.info('core timedate :',eachcrash['core-time-date'])
                except:
                    pass
                    self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                #verify any hardware errors in device
                # try:
                #     hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                #     if hardwareErrorres.status_code == 200:
                #         self.logger.info('Fetching hardware errors')
                #         data = json.loads(hardwareErrorres.content)['data']
                #         if not data:
                #             table_result.append(['Test Hardware errors: ', 'PASS'])
                #             self.logger.info('Hardware errors are not seen')
                #         else:
                #             self.logger.info(' ******** Found hardware errors ********** ')
                #             table_result.append(['Test Hardware errors: ', 'FAIL'])
                #             for eacherror in data :
                #                 if eacherror['vdevice-host-name'] == device:
                #                     self.logger.info('Hardware errors are seen on device [%s]' % device)
                #                     self.logger.info('alarm-description:',eacherror['alarm-description'])
                #                     self.logger.info('alarm-time:',eacherror['alarm-time'])
                #                     self.logger.info('alarm-category:',eacherror['alarm-time'])
                #                 else:
                #                     self.logger.info('Hardware errors are not seen on device [%s]' % device)
                # except:
                #     pass
                #     self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
                #Get bfd sessions output after reboot
                try:
                    res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        table_result.append(['Test BFD Sessions up after Reboot: ', 'PASS'])
                        bfdSessionsUpAfterReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                        self.logger.info('Bfd Sessions up after Reboot: [%s]' % bfdSessionsUpAfterReboot)
                    if bfdSessionsUpAfterReboot != bfdSessionsUpbeforeReboot:
                        table_result.append(['Test BFD Sessions up after Reboot: ', 'FAIL'])
                        self.logger.info('BFD session count did not match on iteration: {}'.format(i))
                        bfdSessionFlag.append(device)
                except:
                    pass
                    self.logger.info('Unable to fetch bfd summary on iteration: {}'.format(i))
                #Get omp peer check summary after reboot
                try:
                    res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        tlocSentafterreboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                        tlocRecievedafterreboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                        vSmartpeerafterreboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                        operStateafterreboot     =  json.loads(res.content)['data'][0]['operstate']
                        self.logger.info('tloc sent after Reboot: [%s]' % tlocSentafterreboot)
                        self.logger.info('tloc recieved after Reboot: [%s]' % tlocRecievedafterreboot)
                        self.logger.info('vsmart peer  after Reboot: [%s]' % vSmartpeerafterreboot)
                        self.logger.info('operstate after Reboot: [%s]' % operStateafterreboot)
                        table_result.append(['Test OMP peer Sessions up before Reboot: ', 'PASS'])
                    if tlocSentafterreboot != tlocSentbeforeReboot and tlocRecievedafterreboot != tlocRecievedbeforeReboot and vSmartpeerafterreboot != vSmartpeerbeforeReboot and operStatebeforeReboot != operStateafterreboot:
                        self.logger.info('OMP summary did not match on iteration: ')
                        table_result.append(['Test OMP peer Sessions up before Reboot: ', 'FAIL'])
                        ompSessionFlag.append(device)
                except:
                    pass
                    self.logger.info('Unable to fetch OMP peer connection on iteration: {}'.format(i))

                #Remove policies from template
                if 'vedge-ISR' in DEVICE_TYPE[device]:
                    editStatus = self.test_edit_device_template_Remove_policies(device)
                    if editStatus[0]:
                        table_result.append(['Test Remove all policies from template: ', 'PASS'])
                        self.logger.info('Edited template and removed all policies')
                    else:
                        self.logger.info('Not able to edit template')
                        table_result.append(['Test Remove all policies from template: ', 'FAIL'])
                        flag = flag + 1
                ######################## Calling detach template proc ####################
                self.logger.info('******** Template detach on iteration: **********:  {}'.format(i))
                detachresult = self.test_detach_templates_from_devices([device])
                if detachresult:
                    table_result.append(['Test Detach Feature Template: ', 'PASS'])
                    self.logger.info('******** detach successfull on iteration: **********:  {}'.format(i))
                else:
                    table_result.append(['Test Detach Feature Template: ', 'FAIL'])
                    self.logger.info('******** detach failure on iteration: **********:  {}'.format(i))
                    flag = flag + 1

            self.logger.info('******** Completed reboot iteration **********:  {}'.format(i))
            if bfdSessionFlag:
                self.logger.info('BFD session count did not match on iteration: {}'.format(i))
                for device in bfdSessionFlag:
                    self.logger.info('Device [%s]' % device)
            else:
                self.logger.info('BFD session count matched on iteration: {}'.format(i))

            if ompSessionFlag:
                self.logger.info('OMP count did not match on iteration: {}'.format(i))
                for device in ompSessionFlag:
                    self.logger.info('Device [%s]' % device)
            else:
                self.logger.info('OMP count matched on iteration: {}'.format(i))
            table.add_rows(table_result)
        print table.draw()
        if flag == 0:
            return [True, 'Successfully rebooted all the devices']
        else:
            return [False, 'Not able to reboot all the devices']

    #@run.test(['test_Securitypolicy'])
    def test_Securitypolicy(self):
        vpnValue = self.config['VPN']
        vpnentries = [{'vpn': vpnValue}]

        createzbfw = vman_session.config.policy.create_zonelist(profile, None, vpnentries)
        if createzbfw.status_code == 200:
            zoneListId = json.loads(createzbfw.content)['listId']
        getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
        if getdataPrefix.status_code != 200:
               self.logger.info('unable to get dataprefix list')

        else:
            for i in range(len(getdataPrefix.json()['data'])):
                if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                        srcNwRefId = getdataPrefix.json()['data'][i]['listId']
                elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                        destNwRefId = getdataPrefix.json()['data'][i]['listId']

        res = vman_session.config.policy.create_zbfw_policy(profile,None,srcNwRefId,destNwRefId,zoneListId)
        if res.status_code != 200:
            self.logger.info('No response found for ZBF')
        else:
            zbfwpolicyId = json.loads(res.content)['definitionId']
        targetVPNs = ['1','2']
        res = vman_session.config.policy.create_Intrusion_prevention(profile,None,targetVPNs)
        if res.status_code != 200:
            self.logger.info('No response found for IP')
            return [False, 'Not able to create IP']
        InrusionPrevId = json.loads(res.content)['definitionId']
        whitelisturlPattern = 'www.amazon.com'
        whitelistname = 'Amazon'
        res = vman_session.config.policy.create_whitelist_url(profile,None,whitelisturlPattern,whitelistname)
        if res.status_code != 200:
            res = vman_session.config.policy.get_whitelisturl(profile,None)
            whiteListId = json.loads(res.content)['data'][0]['listId']
        blacklisturlPattern = 'www.twitter.com'
        blacklistname = 'twitter'
        res = vman_session.config.policy.create_blacklist_url(profile,None,blacklisturlPattern,blacklistname)
        if res.status_code != 200:
            res = vman_session.config.policy.get_blacklisturl(profile,None)
            blackListId = json.loads(res.content)['data'][0]['listId']
        res = vman_session.config.policy.create_URLF_Policy(profile,None,targetVPNs,whiteListId,blackListId)
        if res.status_code != 200:
            return [False, 'Not able to create URLF']
        URLFpolicyId = json.loads(res.content)['definitionId']
        res = vman_session.config.policy.create_AMP(profile,None,targetVPNs)
        if res.status_code != 200:
            return [False, 'Not able to create AMP']
        AMPpolicyId = json.loads(res.content)['definitionId']
        sequences = [
            {
                'sequenceId'    :   '1',
                'sequenceName'  :   "Rule12",
                'baseAction'    :   "decrypt",
                'sequenceType'  :   "sslDecryption",
                'match'         :   {
                                        'entries' : [
                                            {
                                            'field' : "sourceVpn",
                                            'value' : "1,2"
                                            }
                                                   ]
                                    }
            }
                    ]
        res = vman_session.config.policy.create_TLSSSLPolicy(profile,None,sequences)
        if res.status_code != 200:
            return [False, 'Not able to create TLSSSLPolicy']
        TLSSSLpolicyId = json.loads(res.content)['definitionId']
        InrusionPrevId = str(InrusionPrevId)
        URLFpolicyId = str(URLFpolicyId)
        # URLFpolicyId = ''
        # AMPpolicyId = ''
        AMPpolicyId = str(AMPpolicyId)
        TLSSSLpolicyId = str(TLSSSLpolicyId)
        zbfwpolicyId = str(zbfwpolicyId)
        res = vman_session.config.policy.create_SecurityPolicy(profile,None,zbfwpolicyId,InrusionPrevId,URLFpolicyId,AMPpolicyId,TLSSSLpolicyId)
        if res.status_code != 200:
            return [False, 'Not able to create security policy']
        return [True, 'Able to create security policy']

    # @run.test(['test_localizedPolicy'])
    def test_localizedPolicy(self):
        if self.config['QoS'] == True:
            qos = self.test_create_QOSPolicy()
            if qos:
                self.logger.info('Created QOS policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')
        a = True
        defintion = {
                    'assembly' : [],
                    'settings' : {'flowVisibility' : a, 'appVisibility' : a}
                    }
        res = vman_session.config.policy.createlocalizedPolicy(profile,None,defintion)
        if res.status_code == 200:
            policyId = json.loads(res.content)['policyId']
            return [True,'Created localized policy successfully']
        else:
            return [False,'Not able to create localized policy']

    # @run.test(['test_delete_localizedPolicy'])
    def test_delete_localizedPolicy(self):
        flag = 0
        res = vman_session.config.policy.getlocalizedPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                policyIds = json.loads(res.content)['data']
                for policy in range(len(policyIds)):
                    policyId = policyIds[policy]['policyId']
                    res = vman_session.config.policy.deletelocalizedPolicy(profile,None,policyId)
                    if res.status_code == 200:
                        self.logger.info('Deleted localized policy ids')
                    else:
                        self.logger.info('Not able to delete localized policy ids')
                        flag = flag + 1
        deleteQOS = self.test_delete_QOSPolicy()
        if deleteQOS:
            self.logger.info('able to delete qos successfully')
        else:
            self.logger.info('Not able to delete qos successfully')
            flag = flag + 1
        if flag == 0:
            return [True,'Able to delete localized policy']
        else:
            return [False,'Not able to delete localized policy']


    def test_delete_QOSPolicy(self):
        flag = 0
        res = vman_session.config.policy.getACLPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    ACLId = json.loads(res.content)['data'][i]['definitionId']
                    res = vman_session.config.policy.deleteACLPolicy(profile,None,ACLId)
                    self.logger.info('Able to delete existing ACLs')
        else:
            self.logger.info('Not able to delete existing ACLs')
            flag = flag + 1

        res = vman_session.config.policy.getQOSMapList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    defnitionId = json.loads(res.content)['data'][i]['definitionId']
                    res = vman_session.config.policy.deleteQOSMapList(profile,None,defnitionId)
                self.logger.info('Able to delete QOS Map lists')
        else:
            self.logger.info('Not able to delete QOS Map lists')
            flag = flag + 1


        res = vman_session.config.policy.getClassList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    CLassListId = json.loads(res.content)['data'][i]['listId']
                    res = vman_session.config.policy.deleteClassList(profile,None,CLassListId)
                self.logger.info('Able to delete existing class lists')
        else:
            self.logger.info('Not able to delete existing class lists')
            flag = flag + 1

        if flag == 0:
            return [True,'Able to delete existng policies related to QOS']
        else:
            return [False,'Not able to delete existng policies related to QOS']


    #@run.test(['test_create_QOSPolicy'])
    def test_create_QOSPolicy(self):
        name = 'voice'
        types = 'class'
        queue = "1"
        res = vman_session.config.policy.createClass(profile,None,name,types,queue)
        if res.status_code == 200:
            classReferenceId = json.loads(res.content)['listId']
            self.logger.info('Able to create Class map')
        else:
            return [False,'Not able to create Class map']
            self.logger.info('Not able to create Class map')

        createdataPrefix = self.test_create_dataPrefix()
        if createdataPrefix:
            self.logger.info('data prefix is created')
        else:
            self.logger.info('data prefix is not created')
        getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
        if getdataPrefix.status_code != 200:
               self.logger.info('unable to get dataprefix list')

        else:
            for i in range(len(getdataPrefix.json()['data'])):
                if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                        srcNwRefId = getdataPrefix.json()['data'][i]['listId']
                elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                        destNwRefId = getdataPrefix.json()['data'][i]['listId']

        getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
        if getdataPrefix.status_code == 200:
            for i in range(len(getdataPrefix.json()['data'])):
                    if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                        srcNwRefId = getdataPrefix.json()['data'][i]['listId']

                    elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                        destNwRefId = getdataPrefix.json()['data'][i]['listId']

        res = vman_session.config.policy.createQOSPolicy(profile,None,"QOSPolicy","QOSPolicy",15,9,classReferenceId)
        if res.status_code == 200:
            self.logger.info('Able to create QOS policy')
        else:
            self.logger.info('Not able to create QOS policy')
            return [False,'Not able to create QOS']

        sequence = [{
                        "sequenceId":1,
                        "sequenceName":"Access Control List",
                        "baseAction":"accept",
                        "sequenceType":"acl",
                        "sequenceIpType":"ipv4",
                        "match":{
                                    "entries":[
                                                {
                                                    "field":"sourceDataPrefixList",
                                                    "ref":str(srcNwRefId)
                                                },
                                                {
                                                    "field":"destinationDataPrefixList",
                                                    "ref":str(destNwRefId)
                                                }
                                              ]
                                },
                        "actions":[
                                    {
                                    "type":"class",
                                    "parameter":{
                                        "ref":str(classReferenceId)
                                                }
                                    }
                                  ]
                    }]
        res = vman_session.config.policy.createACLPolicy(profile,None,'ACLPolicy','QOSpolicy',sequence)
        if res.status_code == 200:
            return [True,'Ok']
            self.logger.info('Able to create QOS ACL')
        else:
            self.logger.info('Not able to create QOS ACL')
            return [False,'notok']


    #@run.test(['test_delete_Securitypolicy'])
    def test_delete_Securitypolicy(self):
        res = vman_session.config.policy.get_Security_policy(profile,None)
        if res.status_code == 200:
            policyIds = json.loads(res.content)['data']
            for policy in range(len(policyIds)):
                securityPolicyId = policyIds[policy]['policyId']
                res = vman_session.config.policy.delete_securityPolicy(profile,None,securityPolicyId)
                if res.status_code == 200:
                    self.logger.info('Deleted security policy ids')
        res = vman_session.config.policy.get_zoneBaseFW(profile,None)
        if res.status_code == 200:
            for policy in range(len(json.loads(res.content)['data'])):
                zbfw_pol_id = json.loads(res.content)['data'][policy]['definitionId']
                res = vman_session.config.policy.delete_Zbfw_policy(profile,None,zbfw_pol_id)
                if res.status_code == 200:
                    self.logger.info('Deleted Zone base firewall policy')
        res = vman_session.config.policy.get_ZoneList(profile,None)
        if res.status_code == 200:
            for id in range(len(json.loads(res.content)['data'])):
                listId = json.loads(res.content)['data'][id]['listId']
                res = vman_session.config.policy.deleteZBFWList(profile,None,listId)
                if res.status_code == 200:
                    self.logger.info('Deleted ZBFWList')
        res = vman_session.config.policy.get_Intrusion_prevention(profile,None)
        if res.status_code == 200:
            for policy in range(len(json.loads(res.content)['data'])):
                InrusionPrevId = json.loads(res.content)['data'][policy]['definitionId']
                res = vman_session.config.policy.delete_Intrusionpolicy(profile,None,InrusionPrevId)
                if res.status_code == 200:
                    self.logger.info('Deleted IP')
        res = vman_session.config.policy.get_URLF(profile,None)
        if res.status_code == 200:
            for policy in range(len(json.loads(res.content)['data'])):
                URLFpolicyId = json.loads(res.content)['data'][policy]['definitionId']
                res = vman_session.config.policy.delete_URLFpolicy(profile,None,URLFpolicyId)
                if res.status_code == 200:
                    self.logger.info('Deleted URLF')
        res = vman_session.config.policy.get_AMP(profile,None)
        if res.status_code == 200:
            for policy in range(len(json.loads(res.content)['data'])):
                AMPpolicyId  = json.loads(res.content)['data'][policy]['definitionId']
                res = vman_session.config.policy.delete_AMP(profile,None,AMPpolicyId )
                if res.status_code != 200:
                    self.logger.info('Deleted AMP')
        res = vman_session.config.policy.get_SSL(profile,None)
        if res.status_code == 200:
            for policy in range(len(json.loads(res.content)['data'])):
                TLSSSLpolicyId = json.loads(res.content)['data'][policy]['definitionId']
                res = vman_session.config.policy.delete_TLSSSL(profile,None,TLSSSLpolicyId)
                if res.status_code == 200:
                    self.logger.info('Delete TLSSSL decryption')
        return [True,'Deleted existing policies']


    #@run.test(['test_delete_AppAwareRoutingPolicy'])
    def test_delete_AppAwareRoutingPolicy(self):
        res = vman_session.config.policy.get_appRoute(profile,None)
        if res.status_code == 200:
            for i in range(len(json.loads(res.content)['data'])):
                Id = json.loads(res.content)['data'][i]['definitionId']
                res = vman_session.config.policy.delete_appRoute(profile,None,Id)
                if res.status_code == 200:
                    self.logger.info('Deleted approutes')
            return[True,'Deleted approutes']
        else:
            return[False,'Not able to delete approutes']

    #@run.test(['test_deleteHubSpoke'])
    def test_deleteHubSpoke(self):
        res = vman_session.config.policy.getHubAndSpokeId(profile,None)
        if res.status_code == 200:
            for i in range(len(json.loads(res.content)['data'])):
                if json.loads(res.content)['data'][i]['type'] == 'hubAndSpoke':
                    Id = json.loads(res.content)['data'][i]['definitionId']
                    res = vman_session.config.policy.deleteHubAndSpoke(profile,None,Id)
                    if res.status_code == 200:
                        self.logger.info('Deleted hubspoke topology')
        res = vman_session.config.policy.getTLOCList(profile,None)
        for j in range(len(json.loads(res.content)['data'])):
            Id = json.loads(res.content)['data'][j]['listId']
            res = vman_session.config.policy.deleteTLOCList(profile,None,Id)
            if res.status_code == 200:
                self.logger.info('Deleted TLOCList')

            return[True,'Deleted approutes']
        else:
            return[False,'Not able to delete approutes']


    #@run.test(['test_create_AppAwareRoutingPolicy'])
    def test_create_AppAwareRoutingPolicy(self):
        res = vman_session.config.policy.getSLAClassList(profile,None)
        name = 'Default'
        if res.status_code == 200:
            for i in range(len(res.json()['data'])):
                    if res.json()['data'][i]['name'] == name:
                        id = res.json()['data'][i]['listId']

        getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
        for i in range(len(getdataPrefix.json()['data'])):
            if getdataPrefix.status_code == 200:
                if getdataPrefix.json()['data'][i]['name'] == 'srcNetwork':
                    srcNwRefId = getdataPrefix.json()['data'][i]['listId']

                elif getdataPrefix.json()['data'][i]['name'] == 'destNetwork':
                    destNwRefId = getdataPrefix.json()['data'][i]['listId']

        sequences = [
                        {
                            "sequenceId":1,
                            "sequenceName":"App Route",
                            "sequenceType":"appRoute",
                            "sequenceIpType":"ipv4",
                            "match":{
                                "entries":[
                                            {
                                                    "field"     :   "sourceDataPrefixList",
                                                    "ref"       :   str(srcNwRefId)
                                            },
                                            {
                                                    "field"     :   "destinationDataPrefixList",
                                                    "ref"       :   str(destNwRefId)
                                            }
                                          ]
                                    },
                            "actions":[
                                            {
                                                    "type":"slaClass",
                                                    "parameter":[
                                                                    {
                                                                        "field" :   "name",
                                                                        "ref"   :    str(id)
                                                                    },
                                                                    {
                                                                        "field"     :   "preferredColor",
                                                                        "value"     :   "default"
                                                                    }
                                                                ]
                                            },
                                            {
                                                    "type":"backupSlaPreferredColor",
                                                    "parameter":"biz-internet"
                                            }
                                      ]
                        }
                    ]

        res = vman_session.config.policy.createAppAwareRouting(profile,None,'name','desc',sequences)
        if res.status_code == 200:
            listReferenceId = json.loads(res.content)['definitionId']
            return [True,listReferenceId]
            self.logger.info('Able to create AppAware routing')
        else:
            self.logger.info('Not able to create AppAware routing')
            return [False,'Not able to create appawarerouting']


    # @run.test(['test_delete_all_existing_feature_templates'])
    def test_delete_all_existing_feature_templates(self):
            response = vman_session.config.tmpl.get_feature_templates(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in range(len(template_data)):
                        template_id = template_data[template]['templateId']
                        delres = vman_session.config.tmpl.delete_feature_templates(profile,None,template_id)
                        if delres.status_code == 200:
                            self.logger.info('Successfully deleted all feature templates')
                        else:
                            self.logger.info('Not able to delete feature templates')
            return [True,'Deleted all non default feature templates']


    @run.test(['test_create_feature_template'])
    def test_create_feature_template(self):
            #***** Delete all existing non default feature templates *****
            self.test_delete_all_existing_feature_templates()
            pm_vedges = ['pm9009']
            for device in pm_vedges:
                hostname = device
                device_type = DEVICE_TYPE[device]
                device = []
                device.append(device_type)
                """vpn 0 template """

                jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'vpntemplate.json'))
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)

                template_name = 'template_VPN0' + hostname
                template_desc = 'template_desc' + hostname
                TotalWANIntfs = self.config['machines'][hostname]['Total_wan_intfs']
                value = deepcopy(defintion['ip']['route']['vipValue'][0])


                for i in range(TotalWANIntfs-1):

                    defintion['ip']['route']['vipValue'].insert(i,value)


                for i in range(TotalWANIntfs):

                    defintion['ip']['route']['vipValue'][i]['prefix']['vipVariableName'] = 'prefix_' + str(i)
                    defintion['ip']['route']['vipValue'][i]['next-hop']['vipValue'][0]['address']['vipVariableName'] = 'NextHop_' + str(i)


                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                    defintion, "false")

                if res.status_code != 200:
                    return [False, 'Not able to create vpn0 template for all the devices']
                else:
                    vpn0templateId  = json.loads(res.content)['templateId']


                """vpn 1 template """

                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    defintion["vpn-id"]["vipValue"] = 1
                    del defintion["ip"]["route"]
                template_name = 'template_VPN1' + hostname
                template_desc = 'template_desc' + hostname

                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                defintion, "false")
                vpn1templateId = json.loads(res.content)['templateId']

                if res.status_code != 200:
                    return [False, 'Not able to create template for all the devices']


                """vpn 512 template """

                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    defintion["vpn-id"]["vipValue"] = 512
                    del defintion["ip"]["route"]

                template_name = 'template_VPN512' + hostname
                template_desc = 'template_desc' + hostname
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                defintion, "false")
                vpn512templateId = json.loads(res.content)['templateId']

                """vpn 0 interface template """
                jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'vpninterfaceEthernet.json'))
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)

                TotalWANIntfs = self.config['machines'][hostname]['Total_wan_intfs']
                vpn0IntftemplateIds = []
                vpn0IntfNames = []
                for i in range(TotalWANIntfs):
                    defintion['if-name']['vipVariableName'] = 'WAN_Inf_' + str(i)
                    defintion['ip']['address']['vipVariableName'] = 'Address_intf_' + str(i)
                    defintion['tunnel-interface']['color']['value']['vipType']   =  'constant'
                    defintion['tunnel-interface']['color']['value']['vipValue']  =  self.config['machines'][hostname]['interfaces']['TRANSPORT%s' %(i)]['color']
                    template_name = 'Interface_VPN0' + hostname + 'WAN_Inf_' + str(i)
                    template_desc = 'Interface_desc' + hostname + 'WAN_Inf_' + str(i)

                    res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn_interface", device,"15.0.0",
                                defintion, "false")
                    if res.status_code == 200:
                        vpn0IntftemplateId = json.loads(res.content)['templateId']
                        vpn0IntftemplateIds.append(vpn0IntftemplateId)
                        vpn0IntfNames.append(defintion['if-name']['vipVariableName'])

                """vpn 512 interface template """
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    del defintion["tunnel-interface"]
                template_name = 'Interface_VPN512' + hostname
                template_desc = 'Interface_desc' + hostname
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn_interface", device,"15.0.0",
                                defintion, "false")
                vpn512IntftemplateId = json.loads(res.content)['templateId']

                """vpn 1 interface template """
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    del defintion["tunnel-interface"]
                template_name = 'Interface_VPN1' + hostname
                template_desc = 'Interface_desc' + hostname
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn_interface", device,"15.0.0",
                                    defintion, "false")
                vpn1IntftemplateId = json.loads(res.content)['templateId']

                #Fetch global template ids
                res = vman_session.config.tmpl.get_feature_templates(profile, None)
                templateIds = json.loads(res.content)['data']
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == 'Factory_Default_AAA_CISCO_Template':
                        aaaid = templateIds[data]['templateId']
                        aaaid = str(aaaid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Cisco_BFD_Template':
                        bfdid = templateIds[data]['templateId']
                        bfdid = str(bfdid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Cisco_OMP_ipv46_Template':
                        OMPid = templateIds[data]['templateId']
                        OMPid = str(OMPid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Cisco_Security_Template':
                        securityid = templateIds[data]['templateId']
                        securityid = str(securityid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Cisco_System_Template':
                        systemid = templateIds[data]['templateId']
                        systemid = str(systemid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Cisco_Logging_Template':
                        Loggingid = templateIds[data]['templateId']
                        Loggingid = str(Loggingid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_Global_CISCO_Template':
                        globalid = templateIds[data]['templateId']
                        globalid = str(globalid)


                generalTemplates = [
                    {'templateId'    : aaaid,   'templateType': "cedge_aaa"},
                    {'templateId'    : bfdid, 'templateType': "cisco_bfd"},
                    {'templateId'    : OMPid, 'templateType': "cisco_omp"},
                    {'templateId'    : securityid, 'templateType': "cisco_security"},
                    {'templateId'    : systemid, 'templateType': "cisco_system",
                        'subTemplates': [{'templateId': Loggingid, 'templateType': "cisco_logging"}]
                    },

                    { 'templateId'   : vpn0templateId,
                    'templateType' : "cisco_vpn",
                    'subTemplates' : [
                        #    { 'templateId': vpn0IntftemplateIds[0], 'templateType': "cisco_vpn_interface"},
                        #    { 'templateId': vpn0IntftemplateIds[1], 'templateType': "cisco_vpn_interface"}
                        ]
                    },
                    { 'templateId': vpn512templateId,
                    'templateType': "cisco_vpn",
                    'subTemplates': [
                        { 'templateId': vpn512IntftemplateId, 'templateType': "cisco_vpn_interface"}
                        ]
                    },
                    { 'templateId': vpn1templateId,
                    'templateType': "cisco_vpn",
                    'subTemplates': [
                        { 'templateId': vpn1IntftemplateId, 'templateType': "cisco_vpn_interface"}
                        ]
                    },
                    {'templateId': globalid, 'templateType': "cedge_global"},
                ]
                for i in range(len(generalTemplates)):
                    if generalTemplates[i]['templateId'] == vpn0templateId:
                        for j in range(len(vpn0IntftemplateIds)):
                            generalTemplates[i]['subTemplates'].append({'templateId': vpn0IntftemplateIds[j],'templateType':"cisco_vpn_interface",})

                template_name = hostname + '_Template'
                template_desc = hostname + '_Template'
                res = vman_session.config.tmpl.create_device_template(profile, None,template_name,template_desc,device_type,generalTemplates)
                if res.status_code != 200:
                    return [False, 'not able to create template for all the devices']
                else:
                    if self.config['machines'][hostname]['NAT'] == True:
                        NATStatus = self.test_add_Enable_NAT(hostname)
                        if NATStatus[0]:
                            self.logger.info(NATStatus[1])
                            return[True,'Able to add NAT and create Master template']
                        else:
                            self.logger.info(NATStatus[1])
                            return[False,'Not able to add NAT but created Master template']
                    self.logger.info('able to create template for all the devices')
                    return[True,'Able to create Master template']


    # @run.test(['test_feature_template_Edit_Attach'])
    def test_feature_template_Edit_Attach(self, device):
            hostname = device
            devices = device
            device_type = DEVICE_TYPE[device]
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            system_ip = self.topology.system_ip(device)
            device = []
            device.append(device_type)
            securityPolicyId  = ''
            localizedPolicyId = ''

            """Fetch appqoe template Id"""
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            for data in range(len(templateIds)):
                if templateIds[data]['templateName'] == 'Factory_Default_AppQoE_Standalone_Template':
                    appqoeid = templateIds[data]['templateId']
                    appqoeid = str(appqoeid)
                elif templateIds[data]['templateName'] == 'Factory_Default_UTD_Template':
                    utdid = templateIds[data]['templateId']
                    utdid = str(utdid)

            print(self.config['machines'][devices]['Securitypolicy'])
            if self.config['machines'][devices]['Securitypolicy'] == True:
                """Fetch security policy Id"""
                res = vman_session.config.policy.get_Security_policy(profile, None)
                if res.status_code == 200:
                    securityPolicyId = json.loads(res.content)['data'][0]['policyId']


            if self.config['machines'][devices]['LocalizedPolicy'] == True:
                """Fetch localized policy Id"""
                res = vman_session.config.policy.getlocalizedPolicy(profile, None)
                if res.status_code == 200:
                    localizedPolicyId = json.loads(res.content)['data'][0]['policyId']

            """Get template id"""

            template_name = hostname + '_Template'
            template_desc = hostname + '_Template'
            template_id = None
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == template_name:
                        template_id = template['templateId']
            if template_id is None:
                return [False, 'no template {} found'.format(template_dict["name"])]

            res = vman_session.config.tmpl.get_template_content(profile, None, template_id)
            if res.status_code != 200 :
                self.logger.info('Failed to fetch template content')

            config = res.json()['generalTemplates']


            if self.config['machines'][devices]['Appqoe'] == True:
                config.append({'templateId'    : appqoeid,   'templateType': "appqoe"})


            if self.config['machines'][devices]['Securitypolicy'] == True:
                config.append({'templateId'    : utdid   ,   'templateType': "virtual-application-utd"})

            res = vman_session.config.tmpl.edit_device_template(profile, None, template_id, template_name, template_desc, device_type, config, securityPolicyId,localizedPolicyId)

            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')

            res = vman_session.config.tmpl.verify_dup_ip(profile, None, system_ip,uuid,devices)
            if res.status_code != 200 :
                return [False, 'Failed to click on next button']

            pm_vedges = self.topology.pm_vedge_list()
            for hostname in pm_vedges:
                if hostname == devices :
                    a = self.config['machines'][hostname]['interfaces']
                    for key, value in a.iteritems():
                        if key == 'MGMT' :
                            for k, v in value.iteritems():
                                if k == 'intf':
                                    vpn512InterfaceName = value['intf'][0]

                                elif k == 'ip':
                                    vpn512InterfaceAddress = value['ip']

                        elif key == 'TRANSPORT':
                            for k, v in value.iteritems():
                                if k == 'intf':
                                    vpn0InterfaceName = value['intf'][0]

                                elif k == 'ip':
                                    vpn0InterfaceAddress = value['ip']

                                elif k == 'color':
                                    color = value['color']

                                elif k == 'ipsec':
                                    ipsec = value['ipsec']

                    vpn1InterfaceAddress = self.config['machines'][hostname]['service_side_ip']
                    vpn1InterfaceName    = self.config['machines'][hostname]['service_side_intf']
                    siteId  = self.config['machines'][hostname]['site_id']

            device = [
            {
               "csv-status"                             :           "complete",
               "csv-deviceId"                           :           uuid,
               "csv-deviceIP"                           :           system_ip,
               "csv-host-name"                          :           devices,
               "//system/host-name"                     :           devices,
               "//system/system-ip"                     :           system_ip,
               "//system/site-id"                       :           siteId,
               "/1/vpn_if_name_Test/interface/if-name"              :           vpn1InterfaceName,
               "/1/vpn_if_name_Test/interface/ip/address"           :           vpn1InterfaceAddress + "/24",
               "/512/vpn_if_name_Test/interface/if-name"            :           vpn512InterfaceName,
               "/512/vpn_if_name_Test/interface/ip/address"         :           vpn512InterfaceAddress + "/24",
               "csv-templateId"                                     :           template_id
            }
         ]

            TotalWANIntfs = self.config['machines'][devices]['Total_wan_intfs']
            for i in range(TotalWANIntfs):

                device[0]['/0/vpn-instance/ip/route/prefix_{}/prefix'.format(i)]                          = self.config['machines'][devices]['prefix%s' %(i)]
                device[0]['/0/vpn-instance/ip/route/prefix_{}/next-hop/NextHop_{}/address'.format(i,i)]   = self.config['machines'][devices]['nexthop%s' %(i)]
                device[0]['/0/WAN_Inf_{}/interface/if-name'.format(i)]                                    = self.config['machines'][devices]['interfaces']['TRANSPORT%s' %(i)]['intf'][0]
                device[0]['/0/WAN_Inf_{}/interface/ip/address'.format(i)]                                 = self.config['machines'][devices]['interfaces']['TRANSPORT%s' %(i)]['ip'] + "/24"

            push_response = vman_session.config.tmpl.attach_feature_template(profile, None, template_id, device)

            if push_response.status_code != 200:
                return[False,'Not able to attach template']
            # time.sleep(30)
            res = vman_session.config.policy.get_Lxc_install_status(profile, None)
            lxcInstallprocessId = json.loads(res.content)['data'][0]['processId']
            task_status = "Success"
            task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, lxcInstallprocessId, 120, task_status)
            if task_status[0]:
                self.logger.info('Successfully edited template for [%s]' % device)
                return[True,'Successfully attached appqoe and security policy to template']
            else:
                return[False,'Not able to attach appqoe and security policy template']


    def test_verify_Appqoe_configs(self,device):
            cmd = 'show service-insertion type appqoe service-node-group'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            flag = 0
            time.sleep(300)
            for line in output.split('\n'):
                if 'Current status of SN' in line:
                    if 'Alive' in line:
                        return [True,'Appqoe status is Alive']
                    else:
                        return [False,'Appqoe status is dead']
            return[False,'no output found']


    def test_verify_UTD_configs(self,device):
            cmd = 'show service-insertion type utd service-node-group'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            flag = 0
            for line in output.split('\n'):
                if 'Current status of SN' in line:
                    if 'Alive' in line:
                        return [True,'utd status is Alive']
                    else:
                        return [False,'utd status is dead']
            return[False,'no output found']

    def test_verify_trustpoint_status(self,device):
            cmd = 'show crypto pki trustpoints PROXY-SIGNING-CA status'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            foundCount = 0
            for line in output.split('\n'):
                if 'Issuing CA certificate configured' in line:
                    foundCount += 1
                elif 'Router General Purpose certificate configured' in line:
                    foundCount += 1
                elif 'Last enrollment status' in line:
                    if 'Granted' in line:
                        foundCount += 1
                elif 'Keys generated' in line:
                    if 'Yes' in line:
                        foundCount += 1
                elif 'Issuing CA authenticated' in line:
                    if 'Yes' in line:
                        foundCount += 1
                elif 'Certificate request' in line:
                    if 'Yes' in line:
                        foundCount += 1

                if foundCount == 6:
                    return [True, 'Crypto PKI Trustpoint Status verified']
            self.logger.debug(output)
            return [False, 'Crypto PKI Trustpoint Status not verified']


    def test_sdwan_appqoe_tcpopt_status(self,device):
            cmd = 'show sdwan appqoe tcpopt status'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            match = 0
            for line in output.split('\n'):
                if 'TCP OPT Operational State' in line:
                    if 'RUNNING' in line:
                        match = match + 1
                elif 'TCP Proxy Operational State' in line:
                    if 'RUNNING' in line:
                        match = match + 1
            if match == 2:
                return [True, 'sdwan appqoe tcpopt status is as expected']
            else:
                return [False, 'sdwan appqoe tcpopt status is not as expected']


    def test_appqoe_qfp_active_stats(self,device):

            cmd = 'show platform hardware qfp active feature appqoe stats all'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            match = 0
            for line in output.split('\n'):
                if 'SN Index [0 (Green)]' in line:
                    match = match + 1
                    self.logger.info('SN status index is green')
                if 'Divert packets/bytes:' in line:
                    match = match + 1
                    self.logger.info('Divert packets/bytes counter got increased')
                if 'Reinject packets/bytes' in line:
                    match = match + 1
                    self.logger.info('Reinject packets/bytes counter got increased')
            if match == 3:
                return [True, 'qfp active stats is as expected']
            else:
                return [False, 'qfp active stats is not as expected']


    def test_appqoe_RM_resources(self,device):

            cmd = 'show sdwan appqoe rm-resources'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            match = 0
            for line in output.split('\n'):
                if 'System Memory Status' in line:
                    if 'GREEN' in line:
                        match = match + 1
                        self.logger.info('System memory status is green')
                    else:
                        return [False, 'System memory status is not working as expected']
                elif 'Overall HTX health Status' in line:
                    if 'GREEN' in line:
                        match = match + 1
                        self.logger.info('Overall HTX health Status is green')
                    else:
                        return [False, 'Overall HTX health Status is not working as expected']
            if match == 2:
                return [True, 'Appqoe RM resources is as expected']
            else:
                return [False, 'Appqoe RM resources is not as expected']

    def test_UTDStatus(self,device):
            cmd = 'show app-hosting list'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            for line in output.split('\n'):
                if 'utd' in line:
                    if 'RUNNING' in line:
                        return [True,'UTD is in running state']
                    else:
                        return [False,'UTD is not in running state']
            return [False,'No output found']


    def test_tcpProxy_Statistics(self,device):
            #device = 'pm9009'
            cmd = 'show tcpproxy statistics'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            for line in output.split('\n'):
                if 'Total Connections' in line:
                    match = re.match(r'.*:.*', line)
                    if match:
                        line = line.split(':')
                        value = line[1].strip(' ').split()
                        if int(value[0]) > 0:
                            self.logger.info('Total connections are increased to %s' % value)
                            return [True, 'tcpproxy statistics is as expected']
                        else:
                            return[False,'TcpProxy statistics count is zero']
            return [False, 'tcpproxy statistics is not as expected']

    def test_clear_tcpProxy_Statistics(self,device):
        #device = 'pm9009'
        cmd = 'clear tcpproxy statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        return [True, 'tcpproxy statistics are cleared']

    # @run.test(['test_show_version'])
    def test_show_version(self,device):
            device = 'pm9009'
            cmd = 'show sdwan version'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            self.logger.info(output)
            version = [ele for ele in output.split('\n') if '.' in ele]
            return [True, version[0]]


    # @run.test(['test_create_cli_templates'])
    def test_create_cli_templates(self):
        failcount = 0
        PushfailedDevices = []
        pm_vedges = ['pm9009','pm9009']
        for device in pm_vedges:
            device_type = DEVICE_TYPE[device]
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            if '/' in uuid:
                uuid = uuid.replace('/','%2F')
            res = vman_session.config.dev.get_device_running_config(profile,None,uuid)
            system_ip = self.topology.system_ip(device)
            config = self.get_config(res)
            template_name = 'cli_template' + device
            template_desc = 'cli_templatedesc' + device
            """Create template for device"""
            return_status = vman_session.config.tmpl.create_cli_template(profile, None, template_name, template_desc,device_type, config, "file", "false")
            if int(return_status.status_code) != 200:
                return [False, 'Not able to create template for [%s]' % device_type]

        if failcount == 0:
            return [True, 'Successfully created Cli template for all the devices']
        else:
            for device in PushfailedDevices:
                self.logger.info('Failed to create Cli template for [%s]' % device)
            return [False, 'Not able to create template for all the devices']

    # @run.test(['display_datapath_utilization_summary'])
    def display_datapath_utilization_summary(self):
            #device_type = DEVICE_TYPE[device]
            device = 'pm9009'
            cmd = 'show platform hardware qfp active datapath utilization summary'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            self.logger.info(output)
            return [True, 'Platform hardware qfp active datapath utilization summary']

    # @run.test(['display_platform_resources'])
    def display_platform_resources(self):
            #device_type = DEVICE_TYPE[device]
            device = 'pm9009'
            cmd = 'show platform resources'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            for line in output.split('\n'):
                if 'RP0 (ok, active)' in line or 'Control Processor' in line or 'DRAM' in line or 'bootflash' in line or 'ESP0(ok, active)' in line or 'QFP' in line or 'DRAM' in line or 'IRAM' in line or 'CPU Utilization'in line:
                    if 'H' in line:
                        self.logger.info('state displayed is H for %s', format(line))
                    else:
                        self.logger.info('state displayed is not H')
            self.logger.info(output)
            return [True, 'Displayed platform resources output']

    # @run.test(['display_statistics_drop'])
    def display_statistics_drop(self):
            #device_type = DEVICE_TYPE[device]
            device = 'pm9009'
            cmd = 'show platform hardware qfp active statistics drop'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            for line in output.split('\n'):
                if 'Global Drop Stats' in line:
                    self.logger.info(output)
                    return [True, 'Displayed statistics drop result']
            return[False,'No output found for statistics drop']

    # @run.test(['rootca'])
    def rootca(self):
        rootCa = vman_session.config.policy.PKI_config(profile,None)
        if rootCa.status_code != 200:
            return[False,'rootCA is not configured properly']
        return[True,'rootCA is configured properly']


    def test_edit_device_template_Remove_policies(self,device):
            hostname = device
            devices = device
            device_type = DEVICE_TYPE[device]
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            system_ip = self.topology.system_ip(device)
            device = []
            device.append(device_type)
            securityPolicyId  = ''
            localizedPolicyId = ''

            """Get template id"""

            template_name = hostname + '_Template'
            template_desc = hostname + '_Template'
            template_id = None
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == template_name:
                        template_id = template['templateId']

                        if template_id is None:
                            return [False, 'no template {} found'.format(template_dict["name"])]


            res = vman_session.config.tmpl.get_template_content(profile, None, template_id)
            if res.status_code != 200 :
                self.logger.info('Failed to fetch template content')
                return[False,'failed to fetch content']

            config = res.json()['generalTemplates']

            for i in range(len(config)):
                for k,v in config[i].items():
                    if v=='appqoe':
                        config[i].clear()
                        break
                    elif v=='virtual-application-utd':
                        config[i].clear()
                        break

            for i in range(len(config)):
                if {} in config:
                    config.remove({})

            res = vman_session.config.tmpl.edit_device_template(profile, None, template_id, template_name, template_desc, device_type, config, securityPolicyId,localizedPolicyId)

            if res.status_code !=200:
                return [False, 'Failed to edit device template']

            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')

            res = vman_session.config.tmpl.verify_dup_ip(profile, None, system_ip,uuid,devices)
            if res.status_code != 200 :
                return [False, 'Failed to click on next button']

            pm_vedges = self.topology.pm_vedge_list()
            for hostname in pm_vedges:
                if hostname == devices :
                    a = self.config['machines'][hostname]['interfaces']
                    for key, value in a.iteritems():
                        if key == 'MGMT' :
                            for k, v in value.iteritems():
                                if k == 'intf':
                                    vpn512InterfaceName = value['intf'][0]

                                elif k == 'ip':
                                    vpn512InterfaceAddress = value['ip']

                        elif key == 'TRANSPORT':
                            for k, v in value.iteritems():
                                if k == 'intf':
                                    vpn0InterfaceName = value['intf'][0]

                                elif k == 'ip':
                                    vpn0InterfaceAddress = value['ip']

                                elif k == 'color':
                                    color = value['color']

                                elif k == 'ipsec':
                                    ipsec = value['ipsec']

                    vpn1InterfaceAddress = self.config['machines'][hostname]['service_side_ip']
                    vpn1InterfaceName    = self.config['machines'][hostname]['service_side_intf']
                    siteId  = self.config['machines'][hostname]['site_id']

            device = [
            {
               "csv-status"                             :           "complete",
               "csv-deviceId"                           :           uuid,
               "csv-deviceIP"                           :           system_ip,
               "csv-host-name"                          :           devices,
               "//system/host-name"                     :           devices,
               "//system/system-ip"                     :           system_ip,
               "//system/site-id"                       :           siteId,
               "/1/vpn_if_name_Test/interface/if-name"              :           vpn1InterfaceName,
               "/1/vpn_if_name_Test/interface/ip/address"           :           vpn1InterfaceAddress + "/24",
               "/512/vpn_if_name_Test/interface/if-name"            :           vpn512InterfaceName,
               "/512/vpn_if_name_Test/interface/ip/address"         :           vpn512InterfaceAddress + "/24",
               "csv-templateId"                                     :           template_id
            }
         ]

            TotalWANIntfs = self.config['machines'][devices]['Total_wan_intfs']
            for i in range(TotalWANIntfs):

                device[0]['/0/vpn-instance/ip/route/prefix_{}/prefix'.format(i)]                          = self.config['machines'][devices]['prefix%s' %(i)]
                device[0]['/0/vpn-instance/ip/route/prefix_{}/next-hop/NextHop_{}/address'.format(i,i)]   = self.config['machines'][devices]['nexthop%s' %(i)]
                device[0]['/0/WAN_Inf_{}/interface/if-name'.format(i)]                                    = self.config['machines'][devices]['interfaces']['TRANSPORT%s' %(i)]['intf'][0]
                device[0]['/0/WAN_Inf_{}/interface/ip/address'.format(i)]                                 = self.config['machines'][devices]['interfaces']['TRANSPORT%s' %(i)]['ip'] + "/24"

            push_response = vman_session.config.tmpl.attach_feature_template(profile, None, template_id, device)

            if push_response.status_code != 200:
                return[False,'Not able to attach template']
            time.sleep(30)
            res = vman_session.config.policy.get_Lxc_install_status(profile, None)
            lxcInstallprocessId = json.loads(res.content)['data'][0]['processId']
            task_status = "Success"
            task_status = vman_session.config.tmpl.wait_for_push_task_to_complete(profile, None, lxcInstallprocessId, 120, task_status)
            if task_status[0]:
                self.logger.info('Successfully edited template for [%s]' % device)
                return[True,'Successfully edited template']
            else:
                return[False,'Not able to edit template']


    def test_add_Enable_NAT(self,hostname):
            hostname,device = hostname,hostname
            device_type = DEVICE_TYPE[device]
            device = []
            device.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            TotalWANIntfs = self.config['machines'][hostname]['Total_wan_intfs']
            jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'NAT.json'))
            with open(jsonfile) as data_file:
                natConfig =  json.load(data_file)

            for data in range(len(templateIds)):
                for i in range(TotalWANIntfs):
                    template_name = 'Interface_VPN0' + hostname + 'WAN_Inf_' + str(i)
                    template_desc = 'Interface_desc' + hostname + 'WAN_Inf_' + str(i)
                    if templateIds[data]['templateName'] == template_name:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion['nat'] = natConfig
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device,"15.0.0",
                                    defintion, "false",templateIds[data]['templateId'])
                        if res.status_code != 200:
                            self.logger.info('Not able to enable NAT in WAN interface')
                            flag = flag + 1
                        else:
                            self.logger.info('Enabled NAT in WAN interface')

            for data in range(len(templateIds)):
                template_name = 'template_VPN1' + hostname
                template_desc = 'template_desc' + hostname
                if templateIds[data]['templateName'] == template_name:
                    defintion = json.loads(templateIds[data]['templateDefinition'])
                    defintion['ip']['route'] = {
                                                "vipType":"constant",
                                                "vipValue":[
                                                        {
                                                            "prefix":{
                                                                "vipObjectType":"object",
                                                                "vipType":"constant",
                                                                "vipValue":"0.0.0.0/0",
                                                                "vipVariableName":"vpn_ipv4_ip_prefix"
                                                            },
                                                            "vpn":{
                                                                "vipType":"constant",
                                                                "vipObjectType":"object",
                                                                "vipValue":0
                                                            },
                                                            "priority-order":[
                                                                "prefix",
                                                                "vpn"
                                                            ]
                                                        }

                                                            ],
                                                "vipObjectType":"tree",
                                                "vipPrimaryKey":[ "prefix"]
                                                }
                    res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn", device,"15.0.0",
                                    defintion, "false",templateIds[data]['templateId'])
                    if res.status_code != 200:
                        flag = flag + 1
                        self.logger.info('Not able to enable NAT in VPN1 template')
                    else:
                        self.logger.info('Enabled NAT in VPN1 template')
            if flag == 0:
                return['True', 'Enabled NAT successfully']
            else:
                return['False', 'Not able to enable NAT ']


    @run.test(['template_check'])
    def template_check(self):
        template_create_fail     = []
        data_policy_create_fail  = []
        data_policy_activate_fail  = []
        attachFail = []
        flag = 0
        pm_vedges = ['pm9009']

        table_result = []
        Iteration = 1
        for i in range(Iteration):
            for device in pm_vedges:
                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                version = self.test_show_version(device)
                print version
                table_result.append(['sdwan version: '+str(version[1]),''])
                table_result.append(['',''])
                self.logger.info('Clean up of previous policy/template configuration process is initiated')
                editStatus = self.test_edit_device_template_Remove_policies(device)
                if editStatus[0]:
                    table_result.append(['Test Clear Previous Security and Localized policy:' , 'PASS'])
                    self.logger.info('Test Clear Previous Security and Localized policy: PASSED')
                else:
                    table_result.append(['Test Clear Previous Security and Localized policy: ', 'FAIL'])
                    self.logger.info('Test Clear Previous Security and Localized policy: FAILED')
                    flag = flag + 1
            #***Detach template from devices if any *****
            self.logger.info('Detaching templates for Cedge')
            detach = self.test_detach_templates_from_devices(pm_vedges)
            if detach:
                table_result.append(['Test cEdge Detach Previous Templates: ', 'PASS'])
                self.logger.info('Test cEdge Detach Previous Templates is PASSED')
            else:
                table_result.append(['Test cEdge Detach Previous Templates: ', 'FAIL'])
                self.logger.info('Test cEdge Detach Previous Templates is FAILED')
                flag = flag + 1

            #****Delete localized policies ***********
            deleteLocalizedPolicy = self.test_delete_localizedPolicy()
            if deleteLocalizedPolicy:
                table_result.append(['Test Delete Localized policy: ', 'PASS'])
                self.logger.info('Localized policy is deleted')
            else:
                table_result.append(['Test Delete Localized policy: ', 'FAIL'])
                self.logger.info('Localized policy is not deleted')
                flag = flag + 1
            #******Clean up code for vSmart templates***********

            #***Deactivate*****
            # table_result.append(['Deactivate previos tcpOpt DataPolicy'])
            deactivate = self.test_deactivate_tcpOpt_dataPolicy()
            if deactivate:
                table_result.append(['Test vSmart Deactivate Previous TcpOpt DataPolicy: ', 'PASS'])
                self.logger.info('Test vSmart Deactivate Previous TcpOpt DataPolicy is PASSED')
            else:
                table_result.append(['Test vSmart Deactivate Previous TcpOpt DataPolicy: ', 'FAIL'])
                self.logger.info('Test vSmart Deactivate Previous TcpOpt DataPolicy is FAILED')
                flag = flag + 1

            #***Detach templates for vSmart if any *****
            self.logger.info('Detaching templates for vSmart')
            detach = self.test_detach_templates_from_devices(vsmarts)
            if detach:
                table_result.append(['Test vSmart Detach Previous Template: ', 'PASS'])
                self.logger.info('Test vSmart Detach Previous Template is PASSED')
            else:
                table_result.append(['Test vSmart Detach Previous Template: ', 'FAIL'])
                self.logger.info('Test vSmart Detach Previous Template is FAILED')
                flag = flag + 1

            """Get template id and delete existing vSmart templates"""
            template_id = None
            for device in vsmarts:
                template_name = device + '_Template'
                response = vman_session.config.tmpl.get_template(profile, None)
                if response.status_code == 200:
                    template_data = response.json()['data']
                    for template in template_data:
                        if template['templateName'] == template_name:
                            template_id = template['templateId']
                            if template_id is None:
                                self.logger.info('no template {} found'.format(template_dict["name"]))
                            else:
                                delres = vman_session.config.tmpl.delete_template(profile,None,template_id)
                                if delres.status_code == 200:
                                    table_result.append(['Test vSmart Delete Previous Templates','PASS'])
                                    self.logger.info('Test vSmart Delete Previous Templates is PASSED')
                                else:
                                    table_result.append(['Test vSmart Delete Previous Templates','FAIL'])
                                    self.logger.info('Test vSmart Delete Previous Templates is FAILED')
                                    flag = flag + 1

            #*******Delete centralized policies *******
            deletePolicies = self.test_deletedatapolicy()
            self.logger.info('Deleting previous centralized policies:')
            if deletePolicies:
                table_result.append(['Test Delete Centralized Data Policy:', 'PASS'])
                self.logger.info('Test Delete Centralized Data Policy is PASSED')
            else:
                table_result.append(['Test Delete Centralized Data Policy:', 'FAIL'])
                self.logger.info('Test Delete Centralized Data Policy is FAILED')
                flag = flag + 1

            #**********Delete security policy********
            self.logger.info('Deleting Previous Security Policies:')
            deletesecpolicy = self.test_delete_Securitypolicy()
            if deletesecpolicy:
                table_result.append(['Test Delete Security Policy: ', 'PASS'])
                self.logger.info('Test Delete Security Policy is PASSED')
            else:
                table_result.append(['Test Delete Security Policy: ', 'FAIL'])
                self.logger.info('Test Delete Security Policy is FAILED')
                flag = flag + 1

            #******* creating vsmart templates
            self.logger.info('******** Creating Template for vSmart:')
            vsmart_cli_template = self.test_create_cli_templates_for_vSmart()
            if vsmart_cli_template:
                table_result.append(['Test Create vSmart Template: ', 'PASS'])
                self.logger.info('Test Create vSmart Template is PASSED')
            else:
                table_result.append(['Test Create vSmart Template: ', 'FAIL'])
                self.logger.info('Test Create vSmart Template is FAILED')
                flag = flag + 1

            #*******create centralized policy*********
            self.logger.info('Creating datapolicy:')
            data_policy_create = self.test_create_tcpOpt_dataPolicy()
            if data_policy_create:
                table_result.append(['Test Create Centralized Data Policy: ', 'PASS'])
                self.logger.info('Test Create Centralized Data Policy is PASSED')
            else:
                table_result.append(['Test Create Centralized Data Policy: ', 'FAIL'])
                self.logger.info('Test Create Centralized Data Policy is FAILED')
                flag = flag + 1

            #******* Activate data policy*********
            self.logger.info('******** Activating datapolicy:')
            data_policy_activate = self.test_activate_tcpOpt_dataPolicy()
            if data_policy_activate:
                table_result.append(['Test Activate Data Policy: ', 'PASS'])
                self.logger.info('Test Activate Data Policy is PASSED')
            else:
                table_result.append(['Test Activate Data Policy: ', 'FAIL'])
                self.logger.info('Test Activate Data Policy is FAILED')
                flag = flag + 1

            #*******create localized policy*********
            self.logger.info('******** Creating localized policy:')
            localized_policy_create = self.test_localizedPolicy()
            if localized_policy_create:
                table_result.append(['Test Create localized Data Policy: ', 'PASS'])
                self.logger.info('******** Localized Data Policy created successfully')
            else:
                table_result.append(['Test Create localized Data Policy: ', 'FAIL'])
                self.logger.info('******** Localized Device failed to create Data Policy')
                flag = flag + 1


            #********** Do PKI config ********
            self.logger.info('Starting PKI configuration ')
            pkiConfig = self.rootca()
            if pkiConfig:
                table_result.append(['Test PKI configuration: ', 'PASS'])
                self.logger.info('Test PKI configuration is PASSED')
            else:
                table_result.append(['Test PKI configuration: ', 'FAIL'])
                self.logger.info('Test PKI configuration is FAILED')
                flag = flag + 1

            #********** create security policy********
            self.logger.info('Starting Security decrypt policy configuration ')
            create_security_policy = self.test_Securitypolicy()
            if create_security_policy:
                table_result.append(['Test Create Security decrypt policy: ', 'PASS'])
                self.logger.info('Test Create Security decrypt policy is PASSED ')
            else:
                table_result.append(['Test Create Security decrypt policy: ', 'FAIL'])
                self.logger.info('Test Create Security decrypt policy is FAILED ')
                flag = flag + 1

            self.logger.info('Edit the device template and attach the security/appqoe/localizedpolicy/nbar/fnf')
            #*****detail to be given in yaml*********
            for device in pm_vedges:
                attachresult = self.test_feature_template_Edit_Attach(device)
                if attachresult:
                    table_result.append(['Test Feature template Edit and Attach: ', 'PASS'])
                    self.logger.info('Test Feature template Edit and Attach is PASSED')
                else:
                    table_result.append(['Test Feature template Edit and Attach: ', 'FAIL'])
                    self.logger.info('Test Feature template Edit and Attach is FAILED')
                    attachFail.append(device)
                    flag = flag + 1

            # Hardsleep for 3 min for CSR to get generated on device
            time.sleep(150)
            #******** cli checks ***********
            for device in pm_vedges:
                self.logger.info('Starting TCP opt status Verification')
                tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)

                if tcp_opt_status[0]:
                    table_result.append(['Test TCP Optimization running status: ', 'PASS'])
                    self.logger.info('Test TCP Optimization running status is PASSED')
                else:
                    table_result.append(['Test TCP Optimization running status: ', 'FAIL'])
                    self.logger.info('Test TCP Optimization running status is FAILED')
                    flag = flag + 1

                #table.add_rows([['TCPOpt_Status','tcp_opt_status[0]']])
                self.logger.info('Starting Appqoe config Verification')
                appqoeresult = self.test_verify_Appqoe_configs(device)

                if appqoeresult[0]:
                    table_result.append(['Test Appqoe running status: ','PASS'])
                    self.logger.info('Test Appqoe running status is PASSED')
                else:
                    table_result.append(['Test Appqoe running status: ','FAIL'])
                    self.logger.info('Test Appqoe running status is FAILED')
                    flag = flag + 1

                #table.add_rows([['Appqoe_Status','appqoeresult[0]']])
                self.logger.info('Starting UTD config Verification')
                utdresult = self.test_verify_UTD_configs(device)

                if utdresult[0]:
                    table_result.append(['Test Verify UTD config status: ','PASS'])
                    self.logger.info('Test Verify UTD config status is PASSED')
                else:
                    table_result.append(['Test Verify UTD status: ','FAIL'])
                    self.logger.info('Test Verify UTD status is FAILED')
                    flag = flag + 1

                self.logger.info('Starting trustpoint running status Verification')
                trustpointstatus = self.test_verify_trustpoint_status(device)

                if trustpointstatus[0]:
                    table_result.append(['Test Trustpoint configured status: ', 'PASS'])
                    self.logger.info('Test Trustpoint configured status is PASSED')
                else:
                    table_result.append(['Test Trustpoint configured status: ', 'FAIL'])
                    self.logger.info('Test Trustpoint configured status is FAILED')
                    flag = flag + 1

                self.logger.info('Starting utd running Verification')
                utdstatus = self.test_UTDStatus(device)

                if utdstatus[0]:
                    table_result.append(['Test UTD running status: ', 'PASS'])
                    self.logger.info('Test UTD running status is PASSED')
                else:
                    table_result.append(['Test UTD running status: ', 'FAIL'])
                    self.logger.info('Test UTD running status is FAILED')
                    flag = flag + 1

                self.logger.info('Starting TCP proxy statistics Verification:')
                clear_tcp_proxy_statistics = self.test_clear_tcpProxy_Statistics(device)
                if clear_tcp_proxy_statistics[0]:
                    table_result.append(['Test Clear TCP proxy statistics: ', 'PASS'])
                    self.logger.info('Test Clear TCP proxy statistics is PASSED')
                else:
                    table_result.append(['Test Clear TCP proxy statistics: ', 'FAIL'])
                    self.logger.info('Test Clear TCP proxy statistics is FAILED')
                    flag = flag + 1
                #********  Starts the Traffic *****************
                self.logger.info('Starting Ixload Traffic Initialization')
                ixL.reassign_ports()
                ixL.start_ix_traffic()
                self.logger.info('Traffic is running')
                time.sleep(60)
                table_result.append(['Test Ixload Traffic Start: ', 'PASS'])
                #********  ADD TRAFFIC CODE HERE *****************
                self.logger.info('Starting TCP proxy statistics Verification:')
                tcp_proxy_statistics = self.test_tcpProxy_Statistics(device)

                if tcp_proxy_statistics[0]:
                    table_result.append(['Test Verify TCP proxy statistics: ', 'PASS'])
                    self.logger.info('Test Verify TCP proxy statistics is PASSED')
                else:
                    table_result.append(['Test Verify TCP proxy statistics: ', 'FAIL'])
                    self.logger.info('Test Verify TCP proxy statistics is FAILED')
                    flag = flag + 1

                self.logger.info('Starting Qft status Verification:')
                appqoe_qft_status = self.test_appqoe_qfp_active_stats(device)

                if appqoe_qft_status[0]:
                    table_result.append(['Test QfP status: ', 'PASS'])
                    self.logger.info('Test QfP status is PASSED ')
                else:
                    table_result.append(['Test QfP status: ', 'FAIL'])
                    self.logger.info('Test QfP status is FAILED')
                    flag = flag + 1

                self.logger.info('Starting RM resources Verification:')
                appqoe_rm_resuorce_status = self.test_appqoe_RM_resources(device)

                if appqoe_rm_resuorce_status[0]:
                    table_result.append(['Test Verify RM resources: ', 'PASS'])
                    self.logger.info('Test Verify RM resources is PASSED ')
                else:
                    table_result.append(['Test Verify RM resources: ', 'FAIL'])
                    self.logger.info('Test Verify RM resources is FAILED ')
                    flag = flag + 1
                #********  Stops the Traffic *****************
                self.logger.info('Traffic stop and clean up process is initiated')
                ixL.stop_ixload_traffic()
                ixL.cleanup_ix_traffic()
                table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                table.add_rows(table_result)
                print table.draw()
                if flag == 0:
                    return [True,'Testcase executed successfully']
                else:
                    return [False,'Few configs failed']


    def get_config(self,res):
        data = res.content
        data = json.loads(data)
        data = data['config']
        return data

if __name__ == '__main__':
    run.call_all(appqoe_system)
