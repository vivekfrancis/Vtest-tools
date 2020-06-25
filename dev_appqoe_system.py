# !/usr/bin/python
import ipaddress
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
# import script_ixload as ixL
from profile import *
from copy import deepcopy
from collections import OrderedDict
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
sys.path.insert(0, os.path.join(main_dir, 'vmanage'))
sys.path.insert(0, os.path.join(main_dir, 'suites'))
from lib.gvmanage_session.configuration.Templates import Templates
from lib.gvmanage_session import Basics
from lib.vmanage_session.VManageSession import VManageSession
from vmanage.scripts.vmanage_session import VmanageSession
import texttable
from texttable import Texttable
table = Texttable()
table_result = []
from aastha_client import AasthaClient
sys.path.insert(1, '/home/tester/vtest-tools/suites/aastha-py/examples')
from examples_utils import get_default_test_config
cfg_path = os.path.join(os.getcwd(), "aastha-py/examples/resources", "simple_cfg.json")

with open(cfg_path) as file:
    cfg = json.load(file)

loader = cfg["loaders"][0]
loader_scenario = loader["configs"][0]

loader_scenario["scale"] = 100
loader_scenario["run_time"] = 250

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
        # pm_vedges = self.topology.pm_vedge_list()
        pm_vedges = self.topology.pm_vedge_list()
        # vm_vedges = self.topology.vm_vedge_list()
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

        global createMulipleACLS,createMulipleACLSequences
        createMulipleACLS = False
        createMulipleACLSequences = True

        DEVICE_TYPE = {}
        DEVICE_TYPE['vm10']   = 'vedge-CSR-1000v'
        DEVICE_TYPE['vm11']   = 'vedge-CSR-1000v'


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

    #@run.test(['test_create_cli_templates_for_vSmart'])
    def test_create_cli_templates_for_vSmart(self):
        failcount = 0
        PushfailedDevices = []
        for device in vsmarts:
            device_type = "vsmart"
            uuid = http.get_device_property_from_key( "uuid", 'host-name', device)
            res = vman_session.config.dev.get_device_running_config(profile,None,uuid)
            system_ip = self.topology.system_ip(device)
            config = self.get_config(res)
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
        pm_vedges = ['pm9009','pm9009']
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
            # import pdb
            # pdb.set_trace()
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
            for device in vm_vedges:
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
            for device in vm_vedges:

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
            else:
                self.logger.info('Not policy found with given name')

            dataPolicyId  = vman_session.config.policy.get_dataPolicyId(profile, None)
            if dataPolicyId.status_code == 200:
                    if dataPolicyId.json()['data']:
                        for i in range(len(dataPolicyId.json()['data'])):
                            datapolicyRefId = dataPolicyId.json()['data'][i]['definitionId']
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

            getdataPrefix = self.delete_data_prefix()
            if getdataPrefix[0]:
                self.logger.info('Able to delete dataprefixes')
            else:
                self.logger.info('Not able to delete dataprefixes')
            if flag == 0:
                    return [True, 'Able to delet datapolicy']
            else:
                    return [False, 'Not able to delete datapolicy']

    def delete_data_prefix(self):
        flag = 0
        getdataPrefix = vman_session.config.policy.get_dataPrefixlist(profile, None)
        if getdataPrefix.status_code != 200:
            return [False, 'Unable to get dataprefix list']
        else:
            if getdataPrefix.json()['data']:
                for i in range(len(getdataPrefix.json()['data'])):
                    if getdataPrefix.json()['data'][i]['referenceCount'] == 0:
                        RefId = getdataPrefix.json()['data'][i]['listId']
                        deletedataPrefix = vman_session.config.policy.delete_dataPrefixlist(profile, None, RefId)
                        if deletedataPrefix.status_code == 200:
                            self.logger.info('Able to delete dataPrefix')
                        else:
                            self.logger.info('Not Able to delete dataPrefix')
                            flag = flag + 1
            if flag == 0:
                return [True,'Able to delete all dataprefix which has no references']
            else:
                return [False,'Not able to delete dataprefix which has no references']


    def test_create_dataPrefixList(self,BRRouter,DCRouter):
            flag = 0
            dataprefixRefIds = []
            LANInterfaceNetwork = self.test_create_srcNwList(BRRouter)
            LANInterfaceNetwork = LANInterfaceNetwork[1]
            for i in range(len(LANInterfaceNetwork)):
                dataprefixname = 'srcNetwork_' + str(i)
                dataprefixentries = [{'ipPrefix': LANInterfaceNetwork[i]}]
                dataPrefixres = vman_session.config.policy.create_dataPrefix(profile, None,dataprefixname,dataprefixentries)
                if dataPrefixres.status_code != 200:
                    flag = flag + 1
                else:
                    srcNwRefId = json.loads(dataPrefixres.content)['listId']
                    dataprefixRefIds.append(srcNwRefId)
            if flag == 0:
                return [True, dataprefixRefIds]
            else:
                return [False, 'Data prefix is not created']


    def test_create_VPNList(self,BRRouter):
            flag = 0
            vpnRefIds = []
            TotalLANIntfs       = self.config['machines'][BRRouter]['VRFCount']
            vrfStartValue       = self.config['machines'][BRRouter]['VRFStart']
            vrfIncrementValue   = self.config['machines'][BRRouter]['IncrVRF']
            for i in range(TotalLANIntfs):
                vpnname = 'VPN_' + str(i)
                if i == 0:
                    vpnValue = vrfStartValue
                else:
                    vpnValue = vrfStartValue + vrfIncrementValue
                vpnentries = [{'vpn': str(i)}]
                vpnRes = vman_session.config.policy.create_VPN_List(profile, None,vpnname,vpnentries)
                if vpnRes.status_code != 200:
                    flag = flag + 1
                else:
                    vpnRefId = json.loads(vpnRes.content)['listId']
                    vpnRefIds.append(vpnRefId)
            if flag == 0:
                return [True, vpnRefIds]
            else:
                return [False, 'Data prefix is not created']


    def test_create_dataPrefix(self,BRhostname,DChostname):
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
                BRLANAddress = self.config['machines'][BRhostname]['service_side_ip']
                ip = BRLANAddress.split('/')
                BRLANNetwork = '.'.join(ip[0].split('.')[:-1]+["0"]) + '/24'
                dataprefixname = 'srcNetwork'
                dataprefixentries = [{'ipPrefix': str(BRLANNetwork)}]
                dataPrefixres = vman_session.config.policy.create_dataPrefix(profile, None,dataprefixname,dataprefixentries)
                if dataPrefixres.status_code != 200:
                    flag = flag + 1
                else:
                    srcNwRefId = json.loads(dataPrefixres.content)['listId']

           if destNwRefId == '':

                DCLANAddress = self.config['machines'][DChostname]['service_side_ip']
                ip = DCLANAddress.split('/')
                DCLANNetwork = '.'.join(ip[0].split('.')[:-1]+["0"]) + '/24'
                dataprefixname = 'destNetwork'
                dataprefixentries = [{'ipPrefix': str(DCLANNetwork)}]
                dataPrefixres = vman_session.config.policy.create_dataPrefix(profile, None,dataprefixname,dataprefixentries)
                if dataPrefixres.status_code != 200:
                    flag = flag + 1
                else:
                    destNwRefId = json.loads(dataPrefixres.content)['listId']
           if flag == 0:
               return [True, srcNwRefId,destNwRefId]
           else:
               return [False, 'Data prefix is not created']


    def test_create_centralized_datapolicy_with_multiple_datapolicies(self,BRRouter='pm9008',DCRouter='pm9010'):
            datapolicyRefIds    =   []
            createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
            if createdataPrefix[0]:
                self.logger.info('data prefix is created')
                destNwRefId =   createdataPrefix[2]
            else:
                self.logger.info('Failed to create dataprefix list')
            srcNwRefIds = self.test_create_dataPrefixList(BRRouter,DCRouter)
            if srcNwRefIds[0]:
                srcNwRefIds = srcNwRefIds[1]
            else:
                self.logger.info('Failed to create datalists')


            if self.config['machines'][BRRouter]['Datapolicy'] == True:
                sitename    = "datapolicy_" + BRRouter
                siteentries = [{'siteId': str(self.config['machines'][BRRouter]['site_id']) }]
                siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                if siteRes.status_code != 200:
                    self.logger.info('Failed to create sitelist for Datapolicy')
                else:
                    siteReferenceId = json.loads(siteRes.content)['listId']

            vpnRefIds = self.test_create_VPNList(BRRouter)
            if vpnRefIds[0]:
                vpnRefIds = vpnRefIds[1]
            else:
                self.logger.info('Failed to create VPNs')

            for i in range(len(srcNwRefIds)):
                sequence2 = [{
                                'sequenceId'     : 1,
                                'sequenceName'   : "Custom",
                                'baseAction'     : "accept",
                                'sequenceType'   : "data",
                                'sequenceIpType' : "ipv4",
                                'match'          :  {'entries':
                                                    [{'field': "sourceDataPrefixList", 'ref': str(srcNwRefIds[i])},
                                                    {'field': "destinationDataPrefixList", 'ref': destNwRefId}
                                                    ]
                                                    },
                               'actions'        :  [
                                                    {'type': "set", 'parameter': [
                                                                                    {
                                                                                        "field":"dscp",
                                                                                        "value":"30"
                                                                                    }
                                                                                ]}
                                                    ]
                    }
                    ]
                policyName      = 'DataPolicy_' + str(i)
                sequenceresp    = vman_session.config.policy.create_sequence(profile, None,policyName,'description',sequence2)
                if sequenceresp.status_code == 200:
                    datapolicyRefId = json.loads(sequenceresp.content)['definitionId']
                    datapolicyRefIds.append(datapolicyRefId)

            policyDefinition = {'assembly' : [] }

            print(range(len(vpnRefIds)))
            print(range(len(datapolicyRefIds)))

            for i in range(len(vpnRefIds)):
                policyDefinition['assembly'].append({
                                                    'definitionId' : datapolicyRefIds[i],
                                                    'type'         : "data",
                                                    'entries'      :  [{
                                                                            'direction'   : "service",
                                                                            'siteLists'   : [siteReferenceId],
                                                                            'vpnLists'    : [vpnRefIds[i]]
                                                                        }]

                                                })

            resp = vman_session.config.policy.createPolicy(profile, None,policyDefinition)
            if resp.status_code == 200:
                return [True, 'Centralized policy created successfully with multiple data policies']
            else:
                return [False, 'Not able to create Centralized policy with multiple data policies']


    def test_create_centralized_datapolicy_with_multiple_VPNs(self,BRRouter='pm9008',DCRouter='pm9010'):
            datapolicyRefIds    =   []
            createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
            if createdataPrefix[0]:
                self.logger.info('data prefix is created')
                destNwRefId =   createdataPrefix[2]
                srcNwRefId  =   createdataPrefix[1]
            else:
                self.logger.info('Failed to create dataprefix list')

            if self.config['machines'][BRRouter]['Datapolicy'] == True:
                sitename    = "datapolicy_" + BRRouter
                siteentries = [{'siteId': str(self.config['machines'][BRRouter]['site_id']) }]
                siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                if siteRes.status_code != 200:
                    self.logger.info('Failed to create sitelist for Datapolicy')
                else:
                    siteReferenceId = json.loads(siteRes.content)['listId']

            vpnRefIds = self.test_create_VPNList(BRRouter)
            if vpnRefIds[0]:
                vpnRefIds = vpnRefIds[1]
            else:
                self.logger.info('Failed to create VPNs')

            sequence2 = [{
                                'sequenceId'     : 1,
                                'sequenceName'   : "Custom",
                                'baseAction'     : "accept",
                                'sequenceType'   : "data",
                                'sequenceIpType' : "ipv4",
                                'match'          :  {'entries':
                                                    [{'field': "sourceDataPrefixList", 'ref': str(srcNwRefId)},
                                                    {'field': "destinationDataPrefixList", 'ref': destNwRefId}
                                                    ]
                                                    },
                                'actions'        :  [
                                                    {'type': "set", 'parameter': [
                                                                                    {
                                                                                        "field":"dscp",
                                                                                        "value":"30"
                                                                                    }
                                                                                ]}
                                                    ]
                    }]
            policyName      = 'DataPolicy'
            sequenceresp    = vman_session.config.policy.create_sequence(profile, None,policyName,'description',sequence2)
            if sequenceresp.status_code == 200:
                datapolicyRefId = json.loads(sequenceresp.content)['definitionId']
                datapolicyRefIds.append(datapolicyRefId)

            policyDefinition = {'assembly' : [] }

            policyDefinition['assembly'].append({
                                                    'definitionId' : datapolicyRefId,
                                                    'type'         : "data",
                                                    'entries'      :  [{
                                                                            'direction'   : "all",
                                                                            'siteLists'   : [siteReferenceId],
                                                                            'vpnLists'    : vpnRefIds
                                                                        }]

                                                })

            resp = vman_session.config.policy.createPolicy(profile, None,policyDefinition)
            if resp.status_code == 200:
                return [True, 'Centralized policy created successfully with multiple VPNs']
            else:
                return [False, 'Not able to create Centralized policy with multiple VPNs']


    def test_create_centralized_Policy(self,BRRouter,DCRouter):
            dataPrefixres = vman_session.config.policy.get_custom_app(profile, None)
            createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
            if createdataPrefix[0]:
                self.logger.info('data prefix is created')
                srcNwRefId  =   createdataPrefix[1]
                destNwRefId =   createdataPrefix[2]
            else:
                self.logger.info('Failed to create dataprefix list')

            for device in vm_vedges:
                    if self.config['machines'][device]['Datapolicy'] == True:
                        sitename    = "datapolicy_" + device
                        siteentries = [{'siteId': str(self.config['machines'][device]['site_id']) }]
                        siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                        if siteRes.status_code != 200:
                            self.logger.info('Failed to create sitelist for Datapolicy')

                    if self.config['machines'][device]['AppAwareroutingpolicy'] == True:
                        sitename    = "AppAwareroutingpolicy_" + device
                        siteentries = [{'siteId': str(self.config['machines'][device]['site_id']) }]
                        siteRes = vman_session.config.policy.create_SiteList(profile, None,sitename, siteentries)
                        if siteRes.status_code != 200:
                            self.logger.info('Failed to create sitelist for Appaware routing policy')


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


    # @run.test(['Appqoe_events'])
    # def Appqoe_events(self):
    #
    #     ixL.reassign_ports()
    #     ixL.start_ix_traffic()
    #     time.sleep(150)
    #     print('running')
    #     ixL.stop_ixload_traffic()
    #     ixL.cleanup_ix_traffic()

    @run.test(['RebootDevices'])
    def RebootDevices(self):
        # pm_vedges = ['pm9006','pm9008','pm9011','pm9012']
        pm_vedges = ['pm9006']
        failcount = 0
        PushfailedDevices = []
        table_result = []
        for i in range(50):
            bfdSessionFlag = []
            ompSessionFlag = []
            attachFail     = []
            flag = 0
            for device in pm_vedges:

                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                table_result.append(['',''])
                self.logger.info('******** Template attach on iteration: **********:  {}'.format(i))

                #newcode
                if 'vedge_' in self.config['machines'][device]['personality']:
                    attachresult = self.test_create_cli_templates_for_devices(device)
                else:
                    createResult = self.test_create_Device_template(device)
                    if createResult[0]:
                        table_result.append(['Created Master templates ', 'PASS'])
                        self.logger.info('Create Master templates is PASSED')
                    else:
                        table_result.append(['Failed to create Master templates: ', 'FAIL'])
                        self.logger.info('Failed to create Master templates is FAILED')
                        flag = flag + 1

                    attachresult = self.test_Edit_And_Attach_Device_template(device)
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
                if self.config['machines'][device]['Securitypolicy'] == True:
                    tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)

                    if tcp_opt_status[0]:
                        self.logger.info('TCP opt status is running: ')
                    else:
                        flag = flag + 1
                        self.logger.info('TCP opt status is not running:')
                    utdresult = self.test_verify_UTD_configs(device)

                    if utdresult[0]:
                        self.logger.info('UTD is alive')
                    else:
                        flag = flag + 1
                        self.logger.info('utd is not configured')

                    trustpointstatus = self.test_verify_trustpoint_status(device)

                    if trustpointstatus[0]:
                        self.logger.info('trustpoint is configured')
                    else:
                        flag = flag + 1
                        self.logger.info('trustpoint is not configured')

                    utdstatus = self.test_UTDStatus(device)

                    if utdstatus[0]:
                        self.logger.info('utd is running')
                    else:
                        flag = flag + 1
                        self.logger.info('utd is not running')

                if self.config['machines'][device]['Appqoe'] == True:
                    appqoeresult = self.test_verify_Appqoe_configs(device)

                    if appqoeresult[0]:
                        self.logger.info('Appqoe is alive')
                    else:
                        flag = flag + 1
                        self.logger.info('Appqoe is not configured')

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
                except:
                    pass
                    self.logger.info('Caught an exception on reboot for iteration: {}'.format(i))


                if self.config['machines'][device]['Appqoe'] == True:
                    appqoeresult = self.test_verify_Appqoe_configs(device)

                    if appqoeresult[0]:
                        self.logger.info('Appqoe is alive')
                    else:
                        flag = flag + 1
                        self.logger.info('Appqoe is not configured')

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
                            for eachcrash in data :
                                self.logger.info('core time :', eachcrash['core-time'])
                                self.logger.info('core filename :', eachcrash['core-filename'])
                                self.logger.info('core timedate :',eachcrash['core-time-date'])
                except:
                    pass
                    self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                #verify any hardware errors in device
                try:
                    hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                    if hardwareErrorres.status_code == 200:
                        self.logger.info('Fetching hardware errors')
                        data = json.loads(hardwareErrorres.content)['data']
                        if not data:
                            table_result.append(['Test Hardware errors: ', 'PASS'])
                            self.logger.info('Hardware errors are not seen')
                        else:
                            self.logger.info(' ******** Found hardware errors ********** ')
                            for eacherror in data :
                                if eacherror['vdevice-host-name'] == device:
                                    table_result.append(['Test Hardware errors: ', 'FAIL'])
                                    self.logger.info('Hardware errors are seen on device [%s]' % device)
                                    self.logger.info('alarm-description:',eacherror['alarm-description'])
                                    self.logger.info('alarm-time:',eacherror['alarm-time'])
                                    self.logger.info('alarm-category:',eacherror['alarm-time'])
                                else:
                                    self.logger.info('Hardware errors are not seen on device [%s]' % device)
                except:
                    pass
                    self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
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
                    fail = fail + 1

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
        if failcount == 0:
            return [True, 'Successfully rebooted all the devices']
        else:
            for device in PushfailedDevices:
                self.logger.info('Failed to reboot for [%s]' % device)
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


    def test_localizedPolicy(self,BRRouter='pm9008',DCRouter='pm9010'):
        acldefnitionIds = []
        if self.config['QoS'] == True:
            qos = self.test_create_QOSPolicy()
            if qos[0]:
                self.logger.info('Created QOS policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        if self.config['ACL'] == True:
            ACL = self.test_create_Access_control_lists(BRRouter,DCRouter)
            if ACL[0]:
                self.logger.info('Created ACL policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        res = vman_session.config.policy.getQOSMapList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if json.loads(res.content)['data'][i]['name'] == 'QOSPolicy':
                        qosdefnitionId = json.loads(res.content)['data'][i]['definitionId']

        res = vman_session.config.policy.getACLPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if 'ACLPolicy' in json.loads(res.content)['data'][i]['name']:
                        acldefnitionId = json.loads(res.content)['data'][i]['definitionId']
                        acldefnitionIds.append(acldefnitionId)
        a = True
        defintion = {
                    'assembly' : [],
                    'settings' : {}
                    }
        if self.config['QoS'] == True:
            defintion['assembly'].append({
                                    "definitionId"  :   str(qosdefnitionId),
                                    "type"          :   "qosMap"
                                            })

        if self.config['ACL'] == True:
            for i in range(len(acldefnitionIds)):
                defintion['assembly'].append({
                                        "definitionId"  :   str(acldefnitionIds[i]),
                                        "type"          :   "acl"
                                                })
        if self.config['FnF'] == True:
            defintion['settings']['flowVisibility'] = a
        if self.config['Nbar'] == True:
            defintion['settings']['appVisibility'] = a
        res = vman_session.config.policy.createlocalizedPolicy(profile,None,defintion)
        if res.status_code == 200:
            policyId = json.loads(res.content)['policyId']
            return [True,'Created localized policy successfully']
        else:
            return [False,'Not able to create localized policy']

    def create_localizedPolicy_with_multiple_seqences(self,BRRouter='pm9008',DCRouter='pm9010'):
        acldefnitionIds = []
        if self.config['QoS'] == True:
            qos = self.test_create_QOSPolicy()
            if qos[0]:
                self.logger.info('Created QOS policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        if self.config['ACL'] == True:
            ACL = self.test_create_ACL_with_multiple_sequences(BRRouter,DCRouter)
            if ACL[0]:
                self.logger.info('Created ACL policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        res = vman_session.config.policy.getQOSMapList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if json.loads(res.content)['data'][i]['name'] == 'QOSPolicy':
                        qosdefnitionId = json.loads(res.content)['data'][i]['definitionId']

        res = vman_session.config.policy.getACLPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if 'ACLPolicy' in json.loads(res.content)['data'][i]['name']:
                        acldefnitionId = json.loads(res.content)['data'][i]['definitionId']
                        acldefnitionIds.append(acldefnitionId)
        a = True
        defintion = {
                    'assembly' : [],
                    'settings' : {}
                    }
        if self.config['QoS'] == True:
            defintion['assembly'].append({
                                    "definitionId"  :   str(qosdefnitionId),
                                    "type"          :   "qosMap"
                                            })

        if self.config['ACL'] == True:
            for i in range(len(acldefnitionIds)):
                defintion['assembly'].append({
                                        "definitionId"  :   str(acldefnitionIds[i]),
                                        "type"          :   "acl"
                                                })
        if self.config['FnF'] == True:
            defintion['settings']['flowVisibility'] = a
        if self.config['Nbar'] == True:
            defintion['settings']['appVisibility'] = a
        res = vman_session.config.policy.createlocalizedPolicy(profile,None,defintion)
        if res.status_code == 200:
            policyId = json.loads(res.content)['policyId']
            return [True,'Created localized policy successfully']
        else:
            return [False,'Not able to create localized policy']


    def create_localizedPolicy_with_multiple_ACLs(self,BRRouter='pm9008',DCRouter='pm9010'):
        acldefnitionIds = []
        if self.config['QoS'] == True:
            qos = self.test_create_QOSPolicy()
            if qos[0]:
                self.logger.info('Created QOS policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        if self.config['ACL'] == True:
            ACL = self.test_create_multiple_ACL_single_sequences(BRRouter,DCRouter)
            if ACL[0]:
                self.logger.info('Created ACL policy successfully')
            else:
                self.logger.info('Not able to create QOS policy successfully')

        res = vman_session.config.policy.getQOSMapList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if json.loads(res.content)['data'][i]['name'] == 'QOSPolicy':
                        qosdefnitionId = json.loads(res.content)['data'][i]['definitionId']

        res = vman_session.config.policy.getACLPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    if 'ACLPolicy' in json.loads(res.content)['data'][i]['name']:
                        acldefnitionId = json.loads(res.content)['data'][i]['definitionId']
                        acldefnitionIds.append(acldefnitionId)
        a = True
        defintion = {
                    'assembly' : [],
                    'settings' : {}
                    }
        if self.config['QoS'] == True:
            defintion['assembly'].append({
                                    "definitionId"  :   str(qosdefnitionId),
                                    "type"          :   "qosMap"
                                            })

        if self.config['ACL'] == True:
            for i in range(len(acldefnitionIds)):
                defintion['assembly'].append({
                                        "definitionId"  :   str(acldefnitionIds[i]),
                                        "type"          :   "acl"
                                                })
        if self.config['FnF'] == True:
            defintion['settings']['flowVisibility'] = a
        if self.config['Nbar'] == True:
            defintion['settings']['appVisibility'] = a
        res = vman_session.config.policy.createlocalizedPolicy(profile,None,defintion)
        if res.status_code == 200:
            policyId = json.loads(res.content)['policyId']
            return [True,'Created localized policy successfully']
        else:
            return [False,'Not able to create localized policy']


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
        getdataPrefix = self.delete_data_prefix()
        if getdataPrefix[0]:
            self.logger.info('Able to delete dataprefixes')
        else:
            flag = flag + 1
            self.logger.info('Not able to delete dataprefixes')
        if flag == 0:
            return [True,'Able to delete localized policy']
        else:
            return [False,'Not able to delete localized policy']

    def test_delete_QOSPolicy(self):
        flag = 0
        res = vman_session.config.policy.getACLPolicy(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                data = json.loads(res.content)['data']
                for i in range(len(data)):
                    print(data)
                    ACLId = data[i]['definitionId']
                    res = vman_session.config.policy.deleteACLPolicy(profile,None,ACLId)
                    self.logger.info('Able to delete existing ACLs')
        else:
            self.logger.info('Not able to delete existing ACLs')
            flag = flag + 1

        res = vman_session.config.policy.getQOSMapList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    qosId = json.loads(res.content)['data'][i]['definitionId']
                    res = vman_session.config.policy.deleteQOSMapList(profile,None,qosId)
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


    def test_create_QOSPolicy(self):
        classmap = self.create_class_map()
        if classmap[0]:
            classReferenceId = classmap[1]
        else:
            return [False,'Failed to create class Map reference']
        res = vman_session.config.policy.createQOSPolicy(profile,None,"QOSPolicy","QOSPolicy",15,9,classReferenceId)
        if res.status_code == 200:
            self.logger.info('Able to create QOS policy')
            return [True,'Able to create QOS policy']
        else:
            self.logger.info('Not able to create QOS policy')
            return [False,'Not able to create QOS']

    def create_class_map(self):
        name = 'voice'
        types = 'class'
        queue = "1"
        res = vman_session.config.policy.createClass(profile,None,name,types,queue)
        if res.status_code == 200:
            classReferenceId = json.loads(res.content)['listId']
            self.logger.info('Able to create Class map')
            return [True,classReferenceId]
        else:
            return [False,'Not able to create Class map']
            self.logger.info('Not able to create Class map')

    def test_create_Access_control_lists(self,BRRouter,DCRouter):
        res = vman_session.config.policy.getClassList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    classReferenceId = json.loads(res.content)['data'][0]['listId']
                    break
                self.logger.info('Able to get existing class lists')
            else:
                classmap = self.create_class_map()
                if classmap[0]:
                    classReferenceId = classmap[1]
                else:
                    return [False,'Failed to create class Map reference']
        else:
            self.logger.info('Not able to fetch existing class lists')

        createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
        if createdataPrefix[0]:
            self.logger.info('data prefix is created')
            srcNwRefId  =   createdataPrefix[1]
            destNwRefId =   createdataPrefix[2]
        else:
            self.logger.info('Failed to create dataprefix list')
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

        res = vman_session.config.policy.createACLPolicy(profile,None,'ACLPolicy','ACLpolicy',sequence)
        if res.status_code == 200:
            return [True,'Able to create ACL']
            self.logger.info('Able to create ACL')
        else:
            self.logger.info('Not able to create ACL')
            return [False,'Not able to create ACL']


    def test_create_ACL_with_multiple_sequences(self,BRRouter,DCRouter):
        res = vman_session.config.policy.getClassList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    classReferenceId = json.loads(res.content)['data'][0]['listId']
                    break
                self.logger.info('Able to get existing class lists')
            else:
                classmap = self.create_class_map()
                if classmap[0]:
                    classReferenceId = classmap[1]
                else:
                    return [False,'Failed to create class Map reference']
        else:
            self.logger.info('Not able to fetch existing class lists')

        createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
        if createdataPrefix[0]:
            self.logger.info('data prefix is created')
            destNwRefId =   createdataPrefix[2]
        else:
            self.logger.info('Failed to create dataprefix list')
        srcNwRefIds = self.test_create_dataPrefixList(BRRouter,DCRouter)

        if srcNwRefIds[0]:
            srcNwRefIds = srcNwRefIds[1]
        else:
            self.logger.info('Failed to create datalists')
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
                                                    "ref":str(srcNwRefIds[0])
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
        for i in range(len(srcNwRefIds)-1):
            value = deepcopy(sequence[0])
            sequence.insert(i+1,value)

        for i in range(len(srcNwRefIds)-1):
            sequence[i+1]["sequenceId"] = sequence[i]["sequenceId"] + 10
            sequence[i+1]["match"]['entries'][0]['ref'] = str(srcNwRefIds[i+1])

        res = vman_session.config.policy.createACLPolicy(profile,None,'ACLPolicy','ACLpolicy',sequence)
        if res.status_code == 200:
            return [True,'Able to create ACL with multiple Networks']
            self.logger.info('Able to create ACL with multiple Networks')
        else:
            self.logger.info('Not able to create ACL with multiple Networks')
            return [False,'Not able to create ACL with multiple Networks']


    def test_create_multiple_ACL_single_sequences(self,BRRouter,DCRouter):
        flag = 0
        res = vman_session.config.policy.getClassList(profile,None)
        if res.status_code == 200:
            if json.loads(res.content)['data']:
                for i in range(len(json.loads(res.content)['data'])):
                    classReferenceId = json.loads(res.content)['data'][0]['listId']
                    break
                self.logger.info('Able to get existing class lists')
            else:
                classmap = self.create_class_map()
                if classmap[0]:
                    classReferenceId = classmap[1]
                else:
                    return [False,'Failed to create class Map reference']
        else:
            self.logger.info('Not able to fetch existing class lists')

        createdataPrefix = self.test_create_dataPrefix(BRRouter,DCRouter)
        if createdataPrefix[0]:
            self.logger.info('data prefix is created')
            destNwRefId =   createdataPrefix[2]
        else:
            self.logger.info('Failed to create dataprefix list')
        srcNwRefIds = self.test_create_dataPrefixList(BRRouter,DCRouter)

        if srcNwRefIds[0]:
            srcNwRefIds = srcNwRefIds[1]
        else:
            self.logger.info('Failed to create datalists')
        for i in range(len(srcNwRefIds)):
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
                                                        "ref":str(srcNwRefIds[i])
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
            policyName = 'ACLPolicy_' + str(i)
            res = vman_session.config.policy.createACLPolicy(profile,None,policyName,policyName,sequence)
            if res.status_code == 200:
                self.logger.info('Able to create ACL no %s'.format(i))
            else:
                flag = flag + 1
        if flag == 0:
            return [True,'Able to create ACL with multiple Networks']
        else:
            self.logger.info('Not able to create multiple ACLs')
            return [False,'Not able to create multiple ACL']

    # @run.test(['test_delete_Securitypolicy'])
    def test_delete_Securitypolicy(self):
        flag = 0
        res = vman_session.config.policy.get_Security_policy(profile,None)
        if res.status_code == 200:
            policyIds = json.loads(res.content)['data']
            for policy in range(len(policyIds)):
                securityPolicyId = policyIds[policy]['policyId']
                res = vman_session.config.policy.delete_securityPolicy(profile,None,securityPolicyId)
                if res.status_code == 200:
                    self.logger.info('Deleted security policy ids')
                else:
                    flag = flag + 1
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
        if flag == 0:
            return [True,'Deleted existing policies']
        else:
            return [False,'Not able to delete existing policies']

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


    def test_deleteHubSpoke(self):
        flag = 0
        res = vman_session.config.policy.getHubAndSpokeId(profile,None)
        if res.status_code == 200:
            for i in range(len(json.loads(res.content)['data'])):
                if json.loads(res.content)['data'][i]['type'] == 'hubAndSpoke':
                    Id = json.loads(res.content)['data'][i]['definitionId']
                    res = vman_session.config.policy.deleteHubAndSpoke(profile,None,Id)
                    if res.status_code == 200:
                        self.logger.info('Deleted hubspoke topology')
                    else:
                        flag = flag + 1
        res = vman_session.config.policy.getTLOCList(profile,None)
        for j in range(len(json.loads(res.content)['data'])):
            Id = json.loads(res.content)['data'][j]['listId']
            res = vman_session.config.policy.deleteTLOCList(profile,None,Id)
            if res.status_code == 200:
                self.logger.info('Deleted TLOCList')
            else:
                flag = flag + 1
        if flag == 0:
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

    #@run.test(['test_delete_all_existing_feature_templates'])
    def test_delete_all_existing_feature_templates(self):
            response = vman_session.config.tmpl.get_feature_templates(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in range(len(template_data)):
                    template_id = template_data[template]['templateId']
                    deviceattach = template_data[template]['devicesAttached']
                    createdBy = template_data[template]['createdBy']
                    attachedMastersCount = template_data[template]['attachedMastersCount']
                    if deviceattach == 0 and createdBy == 'admin' and attachedMastersCount == 0:
                        delres = vman_session.config.tmpl.delete_feature_templates(profile,None,template_id)
                        if delres.status_code == 200:
                            self.logger.info('Successfully deleted all feature templates')
                        else:
                            return [False,'']
                            self.logger.info('Not able to delete feature templates')
            return [True,'Deleted all non default feature templates']

    # @run.test(['test_delete_device_templates'])
    def test_delete_device_templates(self,hostname):
            response = vman_session.config.tmpl.get_template(profile, None)
            if response.status_code == 200:
                template_data = response.json()['data']
                for template in template_data:
                    if template['templateName'] == hostname + '_Template':
                        template_id = template['templateId']
                        delres = vman_session.config.tmpl.delete_template(profile,None,template_id)
                        if delres.status_code == 200:
                            self.logger.info('Successfully deleted all feature templates')
                        else:
                            self.logger.info('Not able to delete feature templates')
            return [True,'Deleted all non default feature templates']

    def convert_To_orderedDict(self,dict):
            ordered_dict = OrderedDict()
            ordered_dict = OrderedDict(sorted(dict.items(),reverse = True))
            return ordered_dict

    #@run.test(['test_create_Device_template'])
    def test_create_Device_template(self,device):
                table_result = []
                flag = 0
                self.test_delete_device_templates(device)
                #***** Delete all existing non default feature templates *****
                self.test_delete_all_existing_feature_templates()
                #for device in pm_vedges:
                table_result.append(['Creating Master template for device: '+str(device),''])
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

                defintion = self.convert_To_orderedDict(defintion)
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

                defintion = self.convert_To_orderedDict(defintion)
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
                defintion = self.convert_To_orderedDict(defintion)
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                defintion, "false")
                vpn512templateId = json.loads(res.content)['templateId']

                # """vpn 0 interface template """
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

                generalTemplatescEdge = [
                    { 'templateId'   : vpn0templateId,
                    'templateType' : "cisco_vpn",
                    'subTemplates' : [
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
                for i in range(len(generalTemplatescEdge)):
                    if generalTemplatescEdge[i]['templateId'] == vpn0templateId:
                        for j in range(len(vpn0IntftemplateIds)):
                            generalTemplatescEdge[i]['subTemplates'].append({'templateId': vpn0IntftemplateIds[j],'templateType':"cisco_vpn_interface",})

                if 'cedge_' in self.config['machines'][hostname]['personality']:
                    generalTemplatescEdge.append({'templateId'    : aaaid,       'templateType'  :   "cedge_aaa"})
                    generalTemplatescEdge.append({'templateId'    : bfdid,       'templateType'  :   "cisco_bfd"})
                    generalTemplatescEdge.append({'templateId'    : OMPid,       'templateType'  :   "cisco_omp"})
                    generalTemplatescEdge.append({'templateId'    : securityid,       'templateType'  :   "cisco_security"})
                    generalTemplatescEdge.append({
                                            "templateId":systemid,
                                            "templateType":"cisco_system",
                                            "subTemplates":[
                                                {
                                                "templateId":Loggingid,
                                                "templateType":"cisco_logging"
                                                }
                                                          ]
                                            })
                template_name = hostname + '_Template'
                template_desc = hostname + '_Template'
                if 'cedge_' in self.config['machines'][hostname]['personality']:
                    res = vman_session.config.tmpl.create_device_template(profile, None,template_name,template_desc,device_type,generalTemplatescEdge)

                if res.status_code != 200:
                    flag = flag + 1
                    table_result.append(['Failed to create Master template', 'FAIL'])
                else:
                    table_result.append(['Able to Create Master template', 'PASS'])
                    if self.config['machines'][hostname]['NAT'] == True:
                        NATStatus = self.test_add_Enable_NAT(hostname)
                        if NATStatus[0]:
                            self.logger.info(NATStatus[1])
                            table_result.append(['Enabled NAT', 'PASS'])
                        else:
                            self.logger.info(NATStatus[1])
                            table_result.append(['Failed to enable NAT', 'FAIL'])
                            flag = flag + 1
                    self.logger.info('able to create template for all the devices')

                table.add_rows(table_result)
                print table.draw()
                if flag == 0:
                    return[True,'Able to create Master template']
                else:
                    return[False,'Not able to create Master template']


    def test_create_Device_template_for_vEdges(self,device):
                table_result = []
                flag = 0
                self.test_delete_device_templates(device)
                #***** Delete all existing non default feature templates *****
                self.test_delete_all_existing_feature_templates()
                #for device in pm_vedges:
                table_result.append(['Creating Master template for device: '+str(device),''])
                hostname = device
                device_type = DEVICE_TYPE[device]
                device = []
                device.append(device_type)

                """system template """
                if 'vedge_' in self.config['machines'][hostname]['personality']:
                    if self.config['machines'][hostname]['EnableTCPOpt']:
                        vedgesystemid_withTCPOpt = self.create_system_template(hostname,device)

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

                defintion = self.convert_To_orderedDict(defintion)
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge", device,"15.0.0",
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
                #Enable TCPOpt on VPN1 template
                if 'vedge_' in self.config['machines'][hostname]['personality']:
                    if self.config['machines'][hostname]['EnableTCPOpt'] == True:
                        defintion.update({'tcp-optimization' : {
                                                                "vipObjectType":"node-only",
                                                                "vipType":"constant",
                                                                "vipValue":"true",
                                                                "vipVariableName":"vpn_tcp_optimization"
                                                            }})

                defintion = self.convert_To_orderedDict(defintion)
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge", device,"15.0.0",
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
                defintion = self.convert_To_orderedDict(defintion)
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge", device,"15.0.0",
                                defintion, "false")
                vpn512templateId = json.loads(res.content)['templateId']

                # """vpn 0 interface template """
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

                    res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge-interface", device,"15.0.0",
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
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge-interface", device,"15.0.0",
                                defintion, "false")
                vpn512IntftemplateId = json.loads(res.content)['templateId']

                """vpn 1 interface template """
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    del defintion["tunnel-interface"]
                template_name = 'Interface_VPN1' + hostname
                template_desc = 'Interface_desc' + hostname
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"vpn-vedge-interface", device,"15.0.0",
                                    defintion, "false")
                vpn1IntftemplateId = json.loads(res.content)['templateId']

                #Fetch global template ids
                res = vman_session.config.tmpl.get_feature_templates(profile, None)
                templateIds = json.loads(res.content)['data']
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == 'Factory_Default_AAA_Template':
                        vedgeaaaid = templateIds[data]['templateId']
                        vedgeaaaid = str(vedgeaaaid)

                    elif 'Factory_Default_BFD_Template' in templateIds[data]['templateName']:
                        vedgebfdid = templateIds[data]['templateId']
                        vedgebfdid = str(vedgebfdid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_vEdge_OMP_Template':
                        vedgeOMPid = templateIds[data]['templateId']
                        vedgeOMPid = str(vedgeOMPid)

                    elif 'Factory_Default_vEdge_Security_Template' in templateIds[data]['templateName']:
                        vedgesecurityid = templateIds[data]['templateId']
                        vedgesecurityid = str(vedgesecurityid)

                    elif templateIds[data]['templateName'] == 'Factory_Default_vEdge_System_Template':
                        vedgesystemid = templateIds[data]['templateId']
                        vedgesystemid = str(vedgesystemid)

                    elif 'Factory_Default_Logging_Template' in templateIds[data]['templateName'] :
                        vedgeLoggingid = templateIds[data]['templateId']
                        vedgeLoggingid = str(vedgeLoggingid)

                generalTemplates = [
                    { 'templateId'   : vpn0templateId,
                    'templateType' : "vpn-vedge",
                    'subTemplates' : [
                        ]
                    },
                    { 'templateId': vpn512templateId,
                    'templateType': "vpn-vedge",
                    'subTemplates': [
                        { 'templateId': vpn512IntftemplateId, 'templateType': "vpn-vedge-interface"}
                        ]
                    },
                    { 'templateId': vpn1templateId,
                    'templateType': "vpn-vedge",
                    'subTemplates': [
                        { 'templateId': vpn1IntftemplateId, 'templateType': "vpn-vedge-interface"}
                        ]
                    }]

                for i in range(len(generalTemplates)):
                    if generalTemplates[i]['templateId'] == vpn0templateId:
                        for j in range(len(vpn0IntftemplateIds)):
                            generalTemplates[i]['subTemplates'].append({'templateId': vpn0IntftemplateIds[j],'templateType':"vpn-vedge-interface",})

                generalTemplates.append({'templateId'    : vedgeaaaid,       'templateType'  :   "aaa"})
                generalTemplates.append({'templateId'    : vedgebfdid,       'templateType'  :   "bfd-vedge"})
                generalTemplates.append({'templateId'    : vedgeOMPid,       'templateType'  :   "omp-vedge"})
                generalTemplates.append({'templateId'    : vedgesecurityid,  'templateType'  :   "security-vedge"})
                if 'vedge_' in self.config['machines'][hostname]['personality']:
                    if self.config['machines'][hostname]['EnableTCPOpt']:
                        generalTemplates.append({
                                                "templateId"    :   vedgesystemid_withTCPOpt[1],
                                                "templateType"  :   "system-vedge",
                                                "subTemplates"  :   [
                                                    {
                                                    "templateId":vedgeLoggingid,
                                                    "templateType":"logging"
                                                    }
                                                            ]
                                                })
                    else:
                        generalTemplates.append({
                                                "templateId":vedgesystemid,
                                                "templateType":"system-vedge",
                                                "subTemplates":[
                                                    {
                                                    "templateId":vedgeLoggingid,
                                                    "templateType":"logging"
                                                    }
                                                            ]
                                                })
                template_name = hostname + '_Template'
                template_desc = hostname + '_Template'
                res = vman_session.config.tmpl.create_device_template(profile, None,template_name,template_desc,device_type,generalTemplates)
                if res.status_code != 200:
                    flag = flag + 1
                    table_result.append(['Failed to create Master template', 'FAIL'])
                else:
                    table_result.append(['Able to Create Master template', 'PASS'])
                    if self.config['machines'][hostname]['NAT'] == True:
                        NATStatus = self.test_add_Enable_NAT(hostname)
                        if NATStatus[0]:
                            self.logger.info(NATStatus[1])
                            table_result.append(['Enabled NAT', 'PASS'])
                        else:
                            self.logger.info(NATStatus[1])
                            table_result.append(['Failed to enable NAT', 'FAIL'])
                            flag = flag + 1
                    self.logger.info('able to create template for all the devices')

                table.add_rows(table_result)
                print table.draw()
                if flag == 0:
                    return[True,'Able to create Master template']
                else:
                    return[False,'Not able to create Master template']

    # @run.test(['test_Edit_And_Attach_Device_template'])
    def test_Edit_And_Attach_Device_template(self, device):
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
            time.sleep(10)
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            for data in range(len(templateIds)):
                if templateIds[data]['templateName'] == 'Factory_Default_AppQoE_Standalone_Template':
                    appqoeid = templateIds[data]['templateId']
                    appqoeid = str(appqoeid)
                elif templateIds[data]['templateName'] == 'Factory_Default_UTD_Template':
                    utdid = templateIds[data]['templateId']
                    utdid = str(utdid)

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
                self.logger.info('added appqoe')

            if self.config['machines'][devices]['Securitypolicy'] == True:
                config.append({'templateId'    : utdid   ,   'templateType': "virtual-application-utd"})
                self.logger.info('added sec policy')

            time.sleep(10)
            res = vman_session.config.tmpl.edit_device_template(profile, None, template_id, template_name, template_desc, device_type, config, securityPolicyId,localizedPolicyId)
            if '%2F' in uuid:
                uuid = uuid.replace('%2F','/')

            res = vman_session.config.tmpl.verify_dup_ip(profile, None, system_ip,uuid,devices)
            if res.status_code != 200 :
                return [False, 'Failed to click on next button']

            pm_vedges = self.topology.vm_vedge_list()
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
            #pdb.set_trace()
            if task_status[0]:
                self.logger.info('Successfully edited template for [%s]' % device)
                return[True,'Successfully attached template to device']
            else:
                return[False,'Not able to attach template to device']


    def test_create_Mastertemplate_with_Subinterfaces(self,device):
            #***** Delete all existing non default feature templates *****
            # pm_vedges = ['pm9009']
            # for device in pm_vedges:
                self.test_delete_device_templates(device)
                self.test_delete_all_existing_feature_templates()
                flag = 0
            # for device in pm_vedges:
                hostname = device
                device_type = DEVICE_TYPE[device]
                device = []
                device.append(device_type)
                # """vpn 0 template """

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

                defintion = self.convert_To_orderedDict(defintion)
                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                    defintion, "false")

                if res.status_code != 200:
                    return [False, 'Not able to create vpn0 template for all the devices']
                else:
                    vpn0templateId  = json.loads(res.content)['templateId']

                #New code##
                """vpn 1 template """
                vpn1templateIds = []
                TotalLANIntfs       = self.config['machines'][hostname]['VRFCount']
                vrfStartValue       = self.config['machines'][hostname]['VRFStart']
                vrfIncrementValue   = self.config['machines'][hostname]['IncrVRF']
                for i in range(TotalLANIntfs):
                    jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'vpntemplate.json'))
                    with open(jsonfile) as data_file:
                        defintion =  json.load(data_file)
                        if i == 0:
                            defintion["vpn-id"]["vipValue"] = vrfStartValue
                            del defintion["ip"]["route"]
                        else:
                            defintion["vpn-id"]["vipValue"] = vrfStartValue + vrfIncrementValue
                            del defintion["ip"]["route"]
                        vrfStartValue = defintion["vpn-id"]["vipValue"]
                    defintion = self.convert_To_orderedDict(defintion)
                    template_name = 'template_VPN1' + hostname + '_' + str(i)
                    template_desc = 'template_desc' + hostname + '_' + str(i)

                    res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn", device,"15.0.0",
                                    defintion, "false")
                    if res.status_code != 200:
                        return [False, 'Not able to create template vpn1 for all the devices']
                    else:
                        vpn1templateId = json.loads(res.content)['templateId']
                        vpn1templateIds.append(vpn1templateId)

                # """vpn 512 template """
                jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'vpntemplate.json'))
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    defintion["vpn-id"]["vipValue"] = 512
                    del defintion["ip"]["route"]

                defintion = self.convert_To_orderedDict(defintion)
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
                ##New code##
                """vpn 1 interface template """
                TotalLANIntfs = self.config['machines'][hostname]['VRFCount']
                vpn1IntftemplateIds = []
                vpn1IntfNames = []
                for i in range(TotalLANIntfs):

                    template_name = 'Interface_VPN01'+ hostname + 'LAN_Inf_' + str(i)
                    template_desc = 'Interface_desc' + hostname + 'LAN_Inf_' + str(i)
                    """vpn 1 interface template """
                    with open(jsonfile) as data_file:
                        defintion =  json.load(data_file)
                        del defintion["tunnel-interface"]
                        defintion['mtu']['vipValue'] = 1496
                        defintion['mtu']['vipType'] = "constant"
                        defintion['if-name']['vipVariableName'] = 'LAN_Inf_' + str(i)
                        defintion['ip']['address']['vipVariableName'] = 'Address_intf_LAN_' + str(i)

                    template_name = 'Interface_VPN1' + hostname + 'LAN_Inf_' + str(i)
                    template_desc = 'Interface_desc' + hostname + 'LAN_Inf_' + str(i)

                    res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn_interface", device,"15.0.0",
                                defintion, "false")
                    if res.status_code == 200:
                        vpn1IntftemplateId = json.loads(res.content)['templateId']
                        vpn1IntftemplateIds.append(vpn1IntftemplateId)
                        vpn1IntfNames.append(defintion['if-name']['vipVariableName'])

                ## LAN Main interface needs to be in VPN 0 ##
                template_name = 'Interface_VPN1'+ hostname + 'LAN_MainInf'
                template_desc = 'Interface_desc' + hostname + 'LAN_MainInf'
                """vpn 1 interface template """
                with open(jsonfile) as data_file:
                    defintion =  json.load(data_file)
                    defintion['if-name']['vipVariableName'] = 'LAN_MainInf'
                    defintion['ip']['address']['vipType'] = 'ignore'
                    del defintion["tunnel-interface"]

                template_name = 'Interface_VPN1' + hostname + 'LAN_MainInf'
                template_desc = 'Interface_desc' + hostname + 'LAN_MainInf'

                res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"cisco_vpn_interface", device,"15.0.0",
                                defintion, "false")
                if res.status_code == 200:
                    vpn1MainIntftemplateId = json.loads(res.content)['templateId']

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
                                                    ]
                                    },
                                    { 'templateId': vpn512templateId,
                                    'templateType': "cisco_vpn",
                                    'subTemplates': [
                                        { 'templateId': vpn512IntftemplateId, 'templateType': "cisco_vpn_interface"}
                                        ]
                                    },
                                    {'templateId': globalid, 'templateType': "cedge_global"},
                                ]
                for i in range(len(generalTemplates)):
                    if generalTemplates[i]['templateId'] == vpn0templateId:
                        generalTemplates[i]['subTemplates'].append({'templateId': vpn1MainIntftemplateId,'templateType':"cisco_vpn_interface"})
                        for j in range(len(vpn0IntftemplateIds)):
                            generalTemplates[i]['subTemplates'].append({'templateId': vpn0IntftemplateIds[j],'templateType':"cisco_vpn_interface"})

                for i in range(TotalLANIntfs):
                    generalTemplates.append(
                                                {   'templateId': vpn1templateIds[i],
                                                    'templateType': "cisco_vpn",
                                                    'subTemplates': [
                                                                        {'templateId'  : vpn1IntftemplateIds[i],
                                                                        'templateType' : "cisco_vpn_interface"}
                                                                    ]
                                                } )

                template_name = hostname + '_Template'
                template_desc = hostname + '_Template'
                res = vman_session.config.tmpl.create_device_template(profile, None,template_name,template_desc,device_type,generalTemplates)
                if res.status_code != 200:
                    flag = flag + 1
                else:
                    if self.config['machines'][hostname]['NAT'] == True:
                        NATStatus = self.test_add_Enable_NAT(hostname)
                        if NATStatus[0]:
                            self.logger.info(NATStatus[1])
                        else:
                            flag = flag + 1
                            self.logger.info(NATStatus[1])
                if flag == 0:
                    self.logger.info('able to create template for all the devices')
                    return[True,'Able to create Master template']
                else:
                    return[False,'Not Able to create Master template']


    def create_system_template(self,hostname,device_type):
        device = device_type
        jsonfile = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../', 'vtest-tools/suites/BglSystemtestbedDeviceConfigs/', 'systemtemplate.json'))
        with open(jsonfile) as data_file:
            defintion =  json.load(data_file)
            defintion["tcp-optimization-enabled"]["vipType"] = 'constant'
            defintion["tcp-optimization-enabled"]["vipValue"] = 'true'
        template_name = 'SystemTemplate_' + hostname
        template_desc = 'SystemTemplate_' + hostname
        res = vman_session.config.tmpl.create_Feature_template(profile, None, template_name, template_desc,"system-vedge", device,"15.0.0",
                                    defintion, "false")
        if res.status_code != 200:
            return [False, 'Not able to create system template for vEdges']
        else:
            SystemtemplateId = json.loads(res.content)['templateId']
            return [True, SystemtemplateId]


    def test_remove_QOS_from_LAN_Intf(self,device,VRFstartcount , VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        del defintion["qos-map"]["vipValue"]
                        defintion["qos-map"]["vipType"]  = 'ignore'
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
                        else:
                            self.logger.info('Able to delete from %s'.format(templateName))
            if flag == 0:
                return [True,'Removed QOS and ACL from interfaces']
            else:
                return [False,'Removed QOS and ACL from interfaces']

    def test_remove_ACL_from_LAN_Intf(self,device,VRFstartcount , VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"] = 'ignore'
                        defintion["access-list"]["vipValue"] = []
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Removed ACL from interfaces']
            else:
                return [False,'Removed ACL from interfaces']

    def test_remove_QOS_from_WAN_Intf(self,device,VRFstartcount , VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN0' + device + 'WAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        del defintion["qos-map"]["vipValue"]
                        defintion["qos-map"]["vipType"]  = 'ignore'
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Removed QOS from interfaces']
            else:
                return [False,'Removed QOS from interfaces']

    def test_remove_ACL_from_WAN_Intf(self,device,VRFstartcount , VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN0' + device + 'WAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"] = 'ignore'
                        defintion["access-list"]["vipValue"] = []
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Removed  ACL from interfaces']
            else:
                return [False,'Removed ACL from interfaces']


    def test_apply_QOS_on_WANInterface(self,device,WANIntfStrtrange , WANIntfEndrange ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(WANIntfStrtrange,WANIntfEndrange+1):
                templateName = 'Interface_VPN0' + device + 'WAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["qos-map"]["vipType"]  = 'constant'
                        defintion["qos-map"]["vipValue"] = 'QOSPolicy'
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Applied QOS on WAN interfaces']
            else:
                return [False,'Not able to apply QOS on WAN interfaces']


    def test_apply_QOS_on_LANInterface(self,device,VRFstartcount = 0, VRFEndcount = 0):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName  = 'Interface_VPN1' + device

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["qos-map"]["vipType"]  = 'constant'
                        defintion["qos-map"]["vipValue"] = 'QOSPolicy'
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Applied QOS on WAN interfaces']
            else:
                return [False,'Not able to apply QOS on WAN interfaces']


    def test_apply_QOS_on_LAN_Sub_Interfaces(self,device,VRFstartcount , VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)

                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["qos-map"]["vipType"]  = 'constant'
                        defintion["qos-map"]["vipValue"] = 'QOSPolicy'
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
            if flag == 0:
                return [True,'Applied QOS on WAN interfaces']
            else:
                return [False,'Not able to apply QOS on WAN interfaces']


    def test_applyACL_on_WANInterface(self,device,WANIntfStrtrange , WANIntfEndrange ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            factorydefault = False
            for i in range(WANIntfStrtrange,WANIntfEndrange+1):
                templateName = 'Interface_VPN0' + device + 'WAN_Inf_' + str(i)
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"]  = 'constant'
                        defintion["access-list"]["vipValue"] =  [{
                                                                                    "acl-name":{
                                                                                        "vipObjectType":"object",
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"ACLPolicy",
                                                                                        "vipVariableName":"ipv4_access_list_egress_acl_name_ipv4"
                                                                                    },
                                                                                    "direction":{
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"out",
                                                                                        "vipObjectType":"object"
                                                                                    },
                                                                                    "priority-order" : ["direction","acl-name"]
                                                                                        }]
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
                        else:
                            self.logger.info('Created for interface %s'.format(templateName))
            if flag == 0:
                return [True,'Applied ACL to WAN interfaces']
            else:
                return [False,'Not able to apply ACL to WAN interfaces']


    def test_applyACL_on_LAN_Interfaces(self,device,VRFstartcount ,VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            factorydefault = False
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"]  = 'constant'
                        defintion["access-list"]["vipValue"] =  [{
                                                                                    "acl-name":{
                                                                                        "vipObjectType":"object",
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"ACLPolicy",
                                                                                        "vipVariableName":"access_list_ingress_acl_name_ipv4"
                                                                                    },
                                                                                    "direction":{
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"in",
                                                                                        "vipObjectType":"object"
                                                                                    },
                                                                                    "priority-order" : ["direction","acl-name"]
                                                                                        }]
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
                        else:
                            self.logger.info('Applied for interface_ %s'.format(templateName))
            if flag == 0:
                return [True,'Applied ACL to LAN interfaces']
            else:
                return [False,'Not able to apply ACL to LAN interfaces']


    def test_apply_SingleACL_on_LAN_SubInterfaces(self,device,VRFstartcount ,VRFEndcount):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            factorydefault = False
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"]  = 'constant'
                        defintion["access-list"]["vipValue"] =  [{
                                                                                    "acl-name":{
                                                                                        "vipObjectType":"object",
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"ACLPolicy",
                                                                                        "vipVariableName":"access_list_ingress_acl_name_ipv4"
                                                                                    },
                                                                                    "direction":{
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"in",
                                                                                        "vipObjectType":"object"
                                                                                    },
                                                                                    "priority-order" : ["direction","acl-name"]
                                                                                        }]
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
                        else:
                            self.logger.info('Applied for interface_ %s'.format(templateName))
            if flag == 0:
                return [True,'Applied ACL to LAN subinterfaces']
            else:
                return [False,'Not able to apply ACL to LAN subinterfaces']


    def test_applyACLs_on_LAN_SubInterfaces(self,device,VRFstartcount ,VRFEndcount ):
            device_type = DEVICE_TYPE[device]
            device_typelist = []
            device_typelist.append(device_type)
            flag = 0
            factorydefault = False
            res = vman_session.config.tmpl.get_feature_templates(profile, None)
            templateIds = json.loads(res.content)['data']
            for i in range(VRFstartcount,VRFEndcount+1):
                templateName = 'Interface_VPN1' + device + 'LAN_Inf_' + str(i)
                for data in range(len(templateIds)):
                    if templateIds[data]['templateName'] == templateName:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        defintion["access-list"]["vipType"]  = 'constant'
                        defintion["access-list"]["vipValue"] =  [{
                                                                                    "acl-name":{
                                                                                        "vipObjectType":"object",
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"ACLPolicy_"+str(i),
                                                                                        "vipVariableName":"access_list_ingress_acl_name_ipv4"
                                                                                    },
                                                                                    "direction":{
                                                                                        "vipType":"constant",
                                                                                        "vipValue":"in",
                                                                                        "vipObjectType":"object"
                                                                                    },
                                                                                    "priority-order" : ["direction","acl-name"]
                                                                                        }]
                        res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device_typelist,"15.0.0",
                                    defintion, factorydefault,templateIds[data]['templateId'])
                        if res.status_code != 200:
                            flag = flag + 1
                        else:
                            self.logger.info('Applied for interface_ %s'.format(templateName))
            if flag == 0:
                return [True,'Applied ACL to LAN subinterfaces']
            else:
                return [False,'Not able to apply ACL to LAN subinterfaces']

    @run.test(['test_Scale_scenario1'])
    def test_Scale_scenario1(self,device='pm9008'):
        flag = 0
        detachresult = self.test_detach_templates_from_devices([device])
        if detachresult[0]:
            self.logger.info(detachresult[1])
        else:
            flag = flag + 1
        createLANSubIntfs =     self.test_create_Mastertemplate_with_Subinterfaces(device)
        if createLANSubIntfs[0]:
            self.logger.info(createLANSubIntfs[1])
        else:
            flag = flag + 1
        delLocalizedPol=     self.test_delete_localizedPolicy()
        if delLocalizedPol[0]:
            self.logger.info(delLocalizedPol[1])
        else:
            flag = flag + 1
        createLocalizedPol=     self.create_localizedPolicy_with_multiple_seqences(BRRouter='pm9008',DCRouter='pm9010')
        if createLocalizedPol[0]:
            self.logger.info(createLocalizedPol[1])
        else:
            flag = flag + 1
        applyQOS_LAN      =     self.test_apply_QOS_on_LAN_Sub_Interfaces(device,0,4)
        if applyQOS_LAN[0]:
            self.logger.info(applyQOS_LAN[1])
        else:
            flag = flag + 1
        applyACL_LAN      =     self.test_apply_SingleACL_on_LAN_SubInterfaces(device,0,4)
        if applyACL_LAN[0]:
            self.logger.info(applyACL_LAN[1])
        else:
            flag = flag + 1
        applyQOS_WAN      =     self.test_apply_QOS_on_WANInterface(device,0,1)
        if applyQOS_WAN[0]:
            self.logger.info(applyQOS_WAN[1])
        else:
            flag = flag + 1
        applyACL_WAN      =     self.test_applyACL_on_WANInterface(device,0,1)
        if applyACL_WAN[0]:
            self.logger.info(applyACL_WAN[1])
        else:
            flag = flag + 1
        attachDevice      =     self.test_Attach_with_SubInterfaces(device)
        if attachDevice[0]:
            self.logger.info(attachDevice[1])
        else:
            flag = flag + 1
        detachresult = self.test_detach_templates_from_devices([device])
        if detachresult[0]:
            self.logger.info(detachresult[1])
        else:
            flag = flag + 1
        removeACLConfigsLAN       = self.test_remove_ACL_from_LAN_Intf(device,0,4)
        if removeACLConfigsLAN[0]:
            self.logger.info(removeACLConfigsLAN[1])
        else:
            flag = flag + 1
        removeQOSConfigsLAN      = self.test_remove_QOS_from_LAN_Intf(device,0,4)
        if removeQOSConfigsLAN[0]:
            self.logger.info(removeQOSConfigsLAN[1])
        else:
            flag = flag + 1
        removeQOSConfigsWAN      = self.test_remove_QOS_from_WAN_Intf(device,0,1)
        if removeQOSConfigsWAN[0]:
            self.logger.info(removeQOSConfigsWAN[1])
        else:
            flag = flag + 1
        removeACLConfigsWAN      = self.test_remove_ACL_from_WAN_Intf(device,0,1)
        if removeQOSConfigsWAN[0]:
            self.logger.info(removeQOSConfigsWAN[1])
        else:
            flag = flag + 1
        attachDevice      =     self.test_Attach_with_SubInterfaces(device)
        if attachDevice[0]:
            self.logger.info(attachDevice[1])
        else:
            flag = flag + 1
        detachresult = self.test_detach_templates_from_devices([device])
        if detachresult[0]:
            self.logger.info(detachresult[1])
        else:
            flag = flag + 1
        if flag == 0:
            return [True,'Executed scalescenario1 successfully with multiple sequences in datapolicy']
        else:
            return [False,'Not able to execute scalescenario1 successfully']

    @run.test(['test_Scale_scenario2'])
    def test_Scale_scenario2(self,device='pm9008'):
        flag = 0
        detachresult = self.test_detach_templates_from_devices([device])
        if detachresult[0]:
            self.logger.info(detachresult[1])
        else:
            flag = flag + 1
        createLANSubIntfs =     self.test_create_Mastertemplate_with_Subinterfaces(device)
        if createLANSubIntfs[0]:
            self.logger.info(createLANSubIntfs[1])
        else:
            flag = flag + 1
        delLocalizedPol=     self.test_delete_localizedPolicy()
        if delLocalizedPol[0]:
            self.logger.info(delLocalizedPol[1])
        else:
            flag = flag + 1
        createLocalizedPol=     self.create_localizedPolicy_with_multiple_ACLs(BRRouter='pm9008',DCRouter='pm9010')
        if createLocalizedPol[0]:
            self.logger.info(createLocalizedPol[1])
        else:
            flag = flag + 1

        applyQOS_LAN      =     self.test_apply_QOS_on_LAN_Sub_Interfaces(device,0,4)
        if applyQOS_LAN[0]:
            self.logger.info(applyQOS_LAN[1])
        else:
            flag = flag + 1
        applyACL_LAN      =     self.test_applyACLs_on_LAN_SubInterfaces(device,0,4)
        if applyACL_LAN[0]:
            self.logger.info(applyACL_LAN[1])
        else:
            flag = flag + 1
        applyQOS_WAN      =     self.test_apply_QOS_on_WANInterface(device,0,1)
        if applyQOS_WAN[0]:
            self.logger.info(applyQOS_WAN[1])
        else:
            flag = flag + 1
        attachDevice      =     self.test_Attach_with_SubInterfaces(device)
        if attachDevice[0]:
            self.logger.info(attachDevice[1])
        else:
            flag = flag + 1
        detachresult = self.test_detach_templates_from_devices([device])
        if detachresult[0]:
            self.logger.info(detachresult[1])
        else:
            flag = flag + 1
        removeACLConfigsLAN       = self.test_remove_ACL_from_LAN_Intf(device,0,4)
        if removeACLConfigsLAN[0]:
            self.logger.info(removeACLConfigsLAN[1])
        else:
            flag = flag + 1
        removeQOSConfigsLAN      = self.test_remove_QOS_from_LAN_Intf(device,0,4)
        if removeQOSConfigsLAN[0]:
            self.logger.info(removeQOSConfigsLAN[1])
        else:
            flag = flag + 1
        removeQOSConfigsWAN      = self.test_remove_QOS_from_WAN_Intf(device,0,1)
        if removeQOSConfigsWAN[0]:
            self.logger.info(removeQOSConfigsWAN[1])
        else:
            flag = flag + 1
        attachDevice      =     self.test_Attach_with_SubInterfaces(device)
        if attachDevice[0]:
            self.logger.info(attachDevice[1])
        else:
            flag = flag + 1

        if flag == 0:
            return [True,'Executed scalescenario2 successfully with multiple datapolicies with one sequence each']
        else:
            return [False,'Not able to execute scalescenario2 successfully']


    @run.test(['test_Scale_scenario3'])
    def test_Scale_scenario3(self,device='pm9008'):
        flag = 0
        #***********CleanUp*********
        cleanup     =   self.deactivate_and_delete_CentralizedPolicy()
        if cleanup[0]:
            self.logger.info(cleanup[1])
        else:
            flag = flag + 1
        #******* creating vsmart templates
        vsmart_cli_template = self.test_create_cli_templates_for_vSmart()
        if vsmart_cli_template[0]:
            self.logger.info('Test Create vSmart Template is PASSED')
        else:
            flag = flag + 1
        #******* Create data policy*********
        create_policy = self.test_create_centralized_datapolicy_with_multiple_VPNs()
        if create_policy[0]:
            self.logger.info('Created centralized Policy')
        else:
            flag = flag + 1
        #******* Activate data policy*********
        data_policy_activate = self.test_activate_tcpOpt_dataPolicy()
        if data_policy_activate:
            self.logger.info('Test Activate Data Policy is PASSED')
        else:
            flag = flag + 1

        if flag == 0:
            return [True,'Executed scalescenario3 successfully']
        else:
            return [False,'Not able to execute scalescenario3 successfully']


    @run.test(['test_Scale_scenario4'])
    def test_Scale_scenario4(self,device='pm9009'):
        flag = 0
        #***********CleanUp*********
        cleanup     =   self.test_detach_templates_from_devices([device])
        cleanup     =   self.test_delete_device_templates(device)
        cleanup     =   self.test_delete_localizedPolicy()
        cleanup     =   self.deactivate_and_delete_CentralizedPolicy()

        if cleanup[0]:
            self.logger.info(cleanup[1])
        else:
            flag = flag + 1
        #******* creating vsmart templates
        vsmart_cli_template = self.test_create_cli_templates_for_vSmart()
        if vsmart_cli_template:
            self.logger.info('Test Create vSmart Template is PASSED')
        else:
            flag = flag + 1
        #******* Create data policy*********
        create_policy = self.test_create_centralized_datapolicy_with_multiple_datapolicies(BRRouter='pm9008',DCRouter='pm9010')
        if create_policy:
            self.logger.info('Create centralized Policy is PASSED')
        else:
            flag = flag + 1
        #******* Activate data policy*********
        data_policy_activate = self.test_activate_tcpOpt_dataPolicy()
        if data_policy_activate:
            self.logger.info('Test Activate Data Policy is PASSED')
        else:
            flag = flag + 1

        if flag == 0:
            return [True,'Executed scalescenario4 successfully']
        else:
            return [False,'Not able to execute scalescenario4 successfully']

    def deactivate_and_delete_CentralizedPolicy(self):
        #***Deactivate*****
        deactivate = self.test_deactivate_tcpOpt_dataPolicy()
        flag = 0
        if deactivate:
            table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'PASS'])
            self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is PASSED')
        else:
            table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'FAIL'])
            self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is FAILED')
            flag = flag + 1
        #*******Delete centralized policies *******
        deletePolicies = self.test_deletedatapolicy()
        self.logger.info('Deleting existing centralized policies:')
        if deletePolicies:
            table_result.append(['Test Delete Centralized Data Policy:', 'PASS'])
            self.logger.info('Test Delete Centralized Data Policy is PASSED')
        else:
            table_result.append(['Test Delete Centralized Data Policy:', 'FAIL'])
            self.logger.info('Test Delete Centralized Data Policy is FAILED')
            flag = flag + 1
        #***Detach templates for vSmart if any *****
        self.logger.info('Detaching templates for vSmart')
        detach = self.test_detach_templates_from_devices(vsmarts)
        if detach:
            table_result.append(['Test vSmart Detach Template: ', 'PASS'])
            self.logger.info('Test vSmart Detach Template is PASSED')
        else:
            table_result.append(['Test vSmart Detach Template: ', 'FAIL'])
            self.logger.info('Test vSmart Detach Template is FAILED')
            flag = flag + 1
        #*****Delete templates **********
        time.sleep(5)
        delete = self.Delete_Templates()
        if delete:
            table_result.append(['Test delete vSmart Template: ', 'PASS'])
            self.logger.info('Test delete vSmart Template is PASSED')
        else:
            table_result.append(['delete vSmart templates: ', 'FAIL'])
            self.logger.info('delete vSmart templates is FAILED')
            flag = flag + 1
        if flag == 0:
            return [True,'Deleted and deactivated datapolicy']
        else:
           return [False,'Not able to delete and deactivate datapolicy']

    def test_Attach_with_SubInterfaces(self,device):
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

            pm_vedges = self.topology.vm_vedge_list()
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
               "//system/site-id"                       :           str(siteId),
               "/0/LAN_MainInf/interface/if-name"       :           vpn1InterfaceName,
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

            TotalLANIntfs = self.config['machines'][devices]['VRFCount']
            ipaddress = self.test_create_ipAddress(devices)
            vrfno      = self.test_fetchVrfNos(devices)
            vrfCount        =   vrfno[1]
            ipaddresslist   =   ipaddress[1]

            for i in range(len(vrfCount)):
                device[0]['/{}/LAN_Inf_{}/interface/if-name'.format(vrfCount[i],i)]     =   vpn1InterfaceName + '.{}'.format(vrfCount[i])
                device[0]['/{}/LAN_Inf_{}/interface/ip/address'.format(vrfCount[i],i)]  =   ipaddresslist[i]

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
                return[True,'Successfully attached appqoe and security policy to template']
            else:
                return[False,'Not able to attach appqoe and security policy template']


    def test_verify_UTD_configs_poll(self,device):
            cmd = 'show service-insertion type utd service-node-group'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            flag = 0
            for line in output.split('\n'):
                if 'Current status of SN' in line:
                    value = line.split(':')
                    if value[1] == 'Alive':
                        return [True,'UTD status is Alive']
                    else:
                        status = self.retry_SN_Status(1,device,cmd,5)
                        if status[0] == True:
                            return [True,'']
                        else:
                            return[False,'Waited for 300 mins for SN to comeup']
            return[False,'no output found']

    #@run.test(['test_verify_Appqoe_configs_poll'])
    def test_verify_Appqoe_configs_poll(self,device):
            cmd = 'show service-insertion type appqoe service-node-group'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            for line in output.split('\n'):
                if 'Current status of SN' in line:
                    value = line.split(':')
                    if value[1] == 'Alive':
                        return [True,'Appqoe status is Alive']
                    else:
                        status = self.retry_SN_Status(30,device,cmd,10)
                        if status[0] == True:
                            return [True,'']
                        else:
                            return[False,'Waited for 300 mins for SN to comeup']
            return[False,'no output found']

    def retry_SN_Status(self,max_tries,device,cmd,wait_time):
        for i in range(max_tries):
            try:
                time.sleep(wait_time)
                SNStatus = self.test_fetch_SN_Status(device,cmd)

                if SNStatus[1] == 'Alive':
                    self.logger.info('Total time taken {} seconds'.format(wait_time * max_tries))
                    return [True]
                    break
                else:
                    return [False]
            except Exception:
                return [False,'']
                continue

    def test_fetch_SN_Status(self,device,cmd):
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            flag = 0
            for line in output.split('\n'):
                if 'Current status of SN' in line:
                    value = line.split(':')
                    SNStatus = value[1].strip()
                    break
            return[True,SNStatus]

    def test_verify_Appqoe_configs(self,device):
            #device = 'pm9009'
            cmd = 'show service-insertion type appqoe service-node-group'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            flag = 0
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

    def test_verify_IP_Sockets(self,device):
            cmd = 'show ip sockets'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            foundCount = 0
            for line in output.split('\n'):
                if '192.168.2.2' in line:
                    self.logger.info('Appqoe socket is available')
                    foundCount = foundCount + 1
                elif '192.0.2.2' in line:
                    self.logger.info('UTD socket is available')
                    foundCount = foundCount + 1
            if foundCount == 2:
                return [True,'Sockets are as expected']
            else:
                return[False,'Only one socket found']


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


    # @run.test(['test_tcpProxy_Statistics'])
    def test_tcpProxy_Statistics(self,device):
            cmd = 'show tcpproxy statistics'
            dest_ip = self.topology.mgmt_ipaddr(device)
            no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0", timeout=300)
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


    @run.test(['verify_tcpOpt_on_vEdges'])
    def verify_tcpOpt_on_vEdges(self):
        flag = 0
        pm_vedges = ['pm9011']
        table_result = []
        Iteration = 1
        BRRouter = 'pm9009'
        DCRouter = 'pm9010'
        try:
            for i in range(Iteration):
                for device in pm_vedges:
                    editStatus = self.test_edit_device_template_Remove_policies(device)
                    if editStatus[0]:
                        table_result.append(['Test remove existing Security and Localized policy:', 'PASS'])
                        self.logger.info('Test remove existing Security and Localized policy: PASSED')
                    else:
                        table_result.append(['Test remove existing Security and Localized policy: ', 'FAIL'])
                        self.logger.info('Test remove existing Security and Localized policy: FAILED')
                        flag = flag + 1
                #***Deactivate*****
                deactivate = self.test_deactivate_tcpOpt_dataPolicy()
                if deactivate:
                    table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'PASS'])
                    self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is PASSED')
                else:
                    table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'FAIL'])
                    self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is FAILED')
                    flag = flag + 1

                #***Detach templates for vSmart if any *****
                self.logger.info('Detaching templates for vSmart')
                detach = self.test_detach_templates_from_devices(vsmarts)
                if detach:
                    table_result.append(['Test vSmart Detach Template: ', 'PASS'])
                    self.logger.info('Test vSmart Detach Template is PASSED')
                else:
                    table_result.append(['Test vSmart Detach Template: ', 'FAIL'])
                    self.logger.info('Test vSmart Detach Template is FAILED')
                    flag = flag + 1

                #*****Delete templates **********
                time.sleep(5)
                delete = self.Delete_Templates()
                if delete:
                    table_result.append(['Test delete vSmart Template: ', 'PASS'])
                    self.logger.info('Test delete vSmart Template is PASSED')
                else:
                    table_result.append(['delete vSmart templates: ', 'FAIL'])
                    self.logger.info('delete vSmart templates is FAILED')
                    flag = flag + 1

                #***Detach template from devices if any *****
                self.logger.info('Detaching templates for Cedge')
                detach = self.test_detach_templates_from_devices(pm_vedges)
                if detach:
                    table_result.append(['Test cEdge Detach Templates: ', 'PASS'])
                    self.logger.info('Test cEdge Detach Templates is PASSED')
                else:
                    table_result.append(['Test cEdge Detach Templates: ', 'FAIL'])
                    self.logger.info('Test cEdge Detach Templates is FAILED')
                    flag = flag + 1

                #*******Delete centralized policies *******
                deletePolicies = self.test_deletedatapolicy()
                self.logger.info('Deleting existing centralized policies:')
                if deletePolicies:
                    table_result.append(['Test Delete Centralized Data Policy:', 'PASS'])
                    self.logger.info('Test Delete Centralized Data Policy is PASSED')
                else:
                    table_result.append(['Test Delete Centralized Data Policy:', 'FAIL'])
                    self.logger.info('Test Delete Centralized Data Policy is FAILED')
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
                data_policy_create = self.test_create_centralized_Policy(BRRouter,DCRouter)
                if data_policy_create[0]:
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

                for device in pm_vedges:
                    #****** create device template for vedges ****
                    create_device_template = self.test_create_Device_template_for_vEdges(device)
                    if data_policy_activate:
                        table_result.append(['Created device template: ', 'PASS'])
                        self.logger.info('Test create device template is PASSED')
                    else:
                        table_result.append(['Test create device template : ', 'FAIL'])
                        self.logger.info('Test create device template  is FAILED')
                        flag = flag + 1

                    attach_device_to_template = self.test_Edit_And_Attach_Device_template(device)
                    if attach_device_to_template:
                        table_result.append(['Attached device to template: ', 'PASS'])
                        self.logger.info('Test Attach device to template is PASSED')
                    else:
                        table_result.append(['Attached device to template : ', 'FAIL'])
                        self.logger.info('Test Attach device to template  is FAILED')
                        flag = flag + 1

                #******** cli checks ***********
                    #********  Starts the Traffic *****************
                    # self.logger.info('Starting Ixload Traffic Initialization')
                    # ixL.reassign_ports()
                    # ixL.start_ix_traffic()
                    # self.logger.info('Traffic is running')
                    # time.sleep(60)
                    # table_result.append(['Test Ixload Traffic Start: ', 'PASS'])
                    #********  ADD TRAFFIC CODE HERE *****************
                    self.logger.info('Verifying tcpopt summary')
                    tcp_opt_summary = self.tcp_opt_summary(device)

                    if tcp_opt_summary[0]:
                        table_result.append(['verified TCPOpt summary: ', 'PASS'])
                        self.logger.info('Test Verify TCP opt summary is PASSED')
                    else:
                        table_result.append(['verified TCPOpt summary: ', 'FAIL'])
                        self.logger.info('Test Verify TCP opt summary is FAILED')
                        flag = flag + 1

                    self.logger.info('Verifying tcpopt active flows')
                    tcp_opt_activeflows = self.tcp_opt_summary_active_flows(device)

                    if tcp_opt_activeflows[0]:
                        table_result.append(['verified TCPOpt active flows: ', 'PASS'])
                        self.logger.info('Test Verify TCP opt active flows is PASSED')
                    else:
                        table_result.append(['verified TCPOpt active flows: ', 'FAIL'])
                        self.logger.info('Test Verify TCP opt active flows is FAILED')
                        flag = flag + 1

                    self.logger.info('Verifying tcpopt expired flows')
                    tcp_opt_expiredflows = self.tcp_opt_summary_expired_flows(device)

                    if tcp_opt_expiredflows[0]:
                        table_result.append(['verified TCPOpt expired flows: ', 'PASS'])
                        self.logger.info('Test Verify TCP opt expired flows is PASSED')
                    else:
                        table_result.append(['verified TCPOpt expired flows: ', 'FAIL'])
                        self.logger.info('Test Verify TCP opt expired flows is FAILED')
                        flag = flag + 1

                    #********  Stops the Traffic *****************
                    self.logger.info('Traffic stop and clean up process is initiated')
                    # ixL.stop_ixload_traffic()
                    # ixL.cleanup_ix_traffic()
                    # table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                    # table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                    # table.add_rows(table_result)


                    #verify crash log details from device
                    time.sleep(5)
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
                                for eachcrash in data :
                                    self.logger.info('core time :', eachcrash['core-time'])
                                    self.logger.info('core filename :', eachcrash['core-filename'])
                                    self.logger.info('core timedate :',eachcrash['core-time-date'])
                                flag = flag + 1
                    except:
                        pass
                        self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))

            table.add_rows(table_result)
            print table.draw()
            if flag == 0:
                return [True,'Verified tcpopt on vedges']
            else:
                return [False,'TCPOpt Verification failed']
        except:
            pass
            table.add_rows(table_result)
            print table.draw()
            self.logger.info('Caught an exception on running testcase during iteration: {}'.format(i))
            return [False,'TCPOpt Verification failed']


    def tcp_opt_summary(self, device):
        cmd = 'show app tcp-opt summary'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        flag = 0
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        self.logger.info(result)
        if result['Optimized flows'] == 0:
            return [False, 'Flows are not optimizied']
        else:
            self.logger.info('optimized flows',result['Optimized flows'])
            return [True,'']



    def tcp_opt_summary_active_flows(self, device):
        serviceSideIp     =    self.config['machines'][device]['service_side_ip']
        LanNetwork        =   '.'.join(serviceSideIp.split('.')[:-1]+["0"]) + '/24'
        cmd = 'show app tcp-opt active-flows'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        flag = 0
        for line in output.split('\n'):
                if '% No entries found' in line:
                    return [False, 'No active flows are found']

                elif 'tcp-state' in line:
                    if "In progress" in line:
                        self.logger.info('TCpState is in progress')
                    else:
                        flag = flag + 1

                vpnregex = re.search("app tcp-opt active-flows vpn \d{1,3}",line)
                if vpnregex:
                    vpnIds = vpnregex.group().split('vpn')
                    vpnid = vpnIds[len(vpnIds)-1]
                srcip = re.search("src-ip \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}",line)
                if srcip:
                    srcips = srcip.group().split('src-ip')
                    srcip = srcips[len(srcips)-1]
                    srcip = srcip.strip(' ')
                    if ipaddress.ip_address(srcip) in ipaddress.ip_network(LanNetwork):
                        self.logger.info('Flows are getting optimized from mentioned srcip')
                    else:
                        flag = flag + 1
                        return [False,'Srcip is incorrect for the obtained flow']
                destip = re.search("dest-ip \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}",line)
                if destip:
                    destips = destip.group().split('dest-ip')
                    destip = destips[len(destips)-1]
        if flag == 0:
            return [True,'Flows are optimized properly']
        else:
            return [False,'Flows are not optimized properly']


    def tcp_opt_summary_expired_flows(self, device):
        cmd = 'show app tcp-opt expired-flows'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        flag = 0
        for line in output.split('\n'):
            if '% No entries found' in line:
                return [False, 'No entries found']
            elif 'tcp-state' in line:
                if "In progress" in line:
                    self.logger.info('TCpState is in progress')
                else:
                    flag = flag + 1
            vpnregex = re.search("app tcp-opt expired-flows vpn \d{1,3}",line)
            if vpnregex:
                    vpnIds = vpnregex.group().split('vpn')
                    vpnid = vpnIds[len(vpnIds)-1]
            srcip = re.search("src-ip \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}",line)
            if srcip:
                    srcips = srcip.group().split('src-ip')
                    srcip = srcips[len(srcips)-1]
                    srcip = srcip.strip(' ')
                    if ipaddress.ip_address(srcip) in ipaddress.ip_network(LanNetwork):
                        self.logger.info('Flows are getting optimized from mentioned srcip')
                    else:
                        flag = flag + 1
                        return [False,'Srcip is incorrect for the obtained flow']
            destip = re.search("dest-ip \d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}",line)
            if destip:
                    destips = destip.group().split('dest-ip')
                    destip = destips[len(destips)-1]
        if flag == 0:
            return [True,'Flows are optimized properly']
        else:
            return [False,'Flows are not optimized properly']



    #@run.test(['test_SSLProxy_Statistics'])
    def test_SSLProxy_Statistics(self,device):
            flag = 0
            cmd = 'show sslproxy statistics'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            statsToBeVerified = ['Total Connections','Proxied Connections']
            for line in output.split('\n'):
                for i in range(len(statsToBeVerified)):
                    if statsToBeVerified[i] in line:
                        match = re.match(r'.*:.*', line)
                        if match:
                            line = line.split(':')
                            value = line[1].strip(' ').split()
                            if int(value[0]) > 0:
                                self.logger.info('{} are increased to {}'.format(statsToBeVerified[i],value))
                            else:
                                flag = flag + 1
                                self.logger.info('{} are only {}'.format(statsToBeVerified[i],value))
                    elif 'Non-proxied Connections' in line:
                        if '0' in line:
                            self.logger.info('Non-proxied connections are still zero')
                        else:
                            flag = flag + 1
            if flag == 0 :
                return [True, 'SSLProxy statistics are as expected']
            else:
                return [False, 'SSLProxy statistics is not as expected']

            # flag = 0
            # cmd = 'show sslproxy statistics'
            # dest_ip = self.topology.mgmt_ipaddr(device)
            # output = self.confd_client.sendline(dest_ip, cmd)
            # print(output)
            # print(type(output))
            # # print(type(output))
            # # output = output['message']
            # # print(type(output))
            # dict_out = self.show_parser1(output)
            # # print(dict_out)
            # print(dict_out['Connection Statistics']['Total Connections'])
            # if dict_out['Connection Statistics']['Total Connections'] > 0 :
            #     print('Total connections are greater than zero')
            #     if dict_out['Connection Statistics']['Proxied Connections'] == dict_out['Connection Statistics']['Total Connections']:
            #         print('Total connections and proxied connections are same')
            # else:
            #     return [False,'']
            # if dict_out['Connection Statistics']['Non-proxied Connections'] == 0 :
            #     return [True,'Non proxied are zero']

    #@run.test(['test_create_cli_templates'])
    def test_create_cli_templates(self):
        failcount = 0
        PushfailedDevices = []
        pm_vedges = ['pm9009']
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

    #@run.test(['hubSpokeCheck'])
    def hubSpokeCheck(self,hostname):
            match = 0
            serviceSideIps = []
            dest_ip = self.topology.mgmt_ipaddr(hostname)
            for device in pm_vedges:
                if device != hostname:
                    if self.config['machines'][device]['Spoke'] == True:
                        serviceSideIp  =   self.config['machines'][device]['service_side_ip']
                        serviceSideIp  =   '.'.join(serviceSideIp.split('.')[:-1]+["0"]) + '/24'
                        serviceSideIps.append(serviceSideIp)

            for device in pm_vedges:
                if self.config['machines'][device]['Hub'] == True:
                    system_ip = self.config['machines'][device]['system_ip']

            for serviceSideIp in range(len(serviceSideIps)):
                if 'vedge_' in self.config['machines'][hostname]['personality']:
                    cmd = 'show omp routes' + ' %s'%(serviceSideIps[serviceSideIp])
                else:
                    cmd = 'show sdwan omp routes' + ' %s'%(serviceSideIps[serviceSideIp])
                output = self.confd_client.sendline(dest_ip, cmd)
                output = output['message']
                print(output)
                for line in output.split('\n'):
                    if system_ip in line:
                        foundCount = 0
                        print(line)
                if  foundCount == 0:
                    match = 0
                else:
                    match = match + 1

            if match == 0 :
                return[True,'']
            else:
                return[False,'']

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


    def rootca(self):
        rootCa = vman_session.config.policy.PKI_config(profile,None)
        if rootCa.status_code != 200:
            return[False,'rootCA is not configured properly']
        return[True,'rootCA is configured properly']

    #@run.test(['test_edit_device_template_Remove_policies'])
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

                        if template['devicesAttached'] == 0:
                            devicesAttached = 0
                        else:
                            devicesAttached = 1
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
            if devicesAttached == 0:
                return [True,'Edited device template and removed policies']
            else:
                if '%2F' in uuid:
                    uuid = uuid.replace('%2F','/')

                res = vman_session.config.tmpl.verify_dup_ip(profile, None, system_ip,uuid,devices)
                if res.status_code != 200 :
                    return [False, 'Failed to click on next button']

                pm_vedges = self.topology.vm_vedge_list()
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
                        if 'vedge_' in self.config['machines'][hostname]['personality']:
                            res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"vpn-vedge-interface", device,"15.0.0",
                                    defintion, "false",templateIds[data]['templateId'])
                        else:
                            res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"cisco_vpn_interface", device,"15.0.0",
                                    defintion, "false",templateIds[data]['templateId'])
                        if res.status_code != 200:
                            self.logger.info('Not able to enable NAT in WAN interface')
                            flag = flag + 1
                        else:
                            self.logger.info('Enabled NAT in WAN interface')
            TotalLANIntfs   =   self.config['machines'][hostname]['VRFCount']
            for data in range(len(templateIds)):
                for i in range(TotalLANIntfs):
                    template_name = 'template_VPN1' + hostname + '_' + str(i)
                    template_desc = 'template_desc' + hostname + '_' + str(i)
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
                        defintion = self.convert_To_orderedDict(defintion)
                        if 'vedge_' in self.config['machines'][hostname]['personality']:
                            res = vman_session.config.tmpl.Edit_Feature_templates(profile, None, templateIds[data]['templateName'], templateIds[data]['templateDescription'],"vpn-vedge", device,"15.0.0",
                                        defintion, "false",templateIds[data]['templateId'])
                        else:
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

    def test_create_ipAddress(self,hostname):
        Network         =   self.config['machines'][hostname]['LANNetwork']
        TotalLANIntfs   =   self.config['machines'][hostname]['VRFCount']
        ip = Network.split('/')
        LANInterfaceAddress = []
        for i in range(TotalLANIntfs):
            interfaceIp = '.'.join(ip[0].split('.')[:-2]+[str(i+1)]+["1"]) + '/24'
            LANInterfaceAddress.append(interfaceIp)
        if LANInterfaceAddress:
            return [True,LANInterfaceAddress]
        else:
            return [False,'Not able to create Interface ips']


    def test_create_srcNwList(self,hostname):
        Network         =   self.config['machines'][hostname]['LANNetwork']
        TotalLANIntfs   =   self.config['machines'][hostname]['VRFCount']
        ip = Network.split('/')
        LANInterfaceNetwork = []
        for i in range(TotalLANIntfs):
            interfaceIp = '.'.join(ip[0].split('.')[:-2]+[str(i+1)]+["0"]) + '/24'
            LANInterfaceNetwork.append(interfaceIp)
        if LANInterfaceNetwork:
            return [True,LANInterfaceNetwork]
        else:
            return [False,'Not able to create Interface ips']

    #@run.test(['test_fetchVrfNos'])
    def test_fetchVrfNos(self,hostname='pm9008'):
        res         =   vman_session.config.tmpl.get_feature_templates(profile, None)
        templateIds =   json.loads(res.content)['data']
        TotalLANIntfs   =   self.config['machines'][hostname]['VRFCount']
        VRF = []
        for data in range(len(templateIds)):
            for i in range(TotalLANIntfs):
                    template_name = 'template_VPN1' + hostname + '_' + str(i)
                    template_desc = 'template_desc' + hostname + '_' + str(i)
                    if templateIds[data]['templateName'] == template_name:
                        defintion = json.loads(templateIds[data]['templateDefinition'])
                        vrfValue = defintion['vpn-id']['vipValue']
                        VRF.append(vrfValue)
        if VRF:
            return [True,sorted(VRF)]
        else:
            return [False,'Not able to fetch VPNIds']

    def test_show_version(self,device):
            cmd = 'show sdwan version'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            self.logger.info(output)
            version = [ele for ele in output.split('\n') if '.' in ele]
            return [True, version[0]]


    def test_clear_tcpProxy_Statistics(self,device):
            #device = 'pm9009'
            cmd = 'clear tcpproxy statistics'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            return [True, 'tcpproxy statistics are cleared']

    def test_clear_SSLProxy_Statistics(self,device):
            #device = 'pm9009'
            cmd = 'clear sslproxy statistics'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            return [True, 'SSLproxy statistics are cleared']

    def key_value_dict(self, line, dictionary):
        match = re.match(r'.*:.*', line)
        if match:
            line = line.split(':')
            key = line[0].strip()
            value = line[1].strip()
            dictionary[key]=int(value)
        return dictionary

    def key_value_dict_str(self, line, dictionary):
        match = re.match(r'.*:.*', line)
        if match:
            line = line.split(':')
            key = line[0].strip()
            value = line[1].strip()
            dictionary[key]=value
        return dictionary

    # @run.test(['verifyURLFStats'])
    def verifyURLFStats(self,device,key='Whitelist Hit Count'):
        cmd = 'show utd engine standard statistics url-filtering | inc {}'.format(key)
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        return result[key]

    # @run.test(['verifytcpproxystats'])
    def verifytcpproxystats(self,device,key='Total Connections'):
        cmd = 'show tcpproxy statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        return result[key]


    # @run.test(['verify_sslproxystatus'])
    def test_sslproxystats(self,device,key,value):
        cmd = 'show sslproxy status'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        if result[key] == value:
            return [True,'']
        else:
            return [False,'']

    # @run.test(['test_UTD_Engine'])
    def test_UTD_Engine(self,device):
        try:
            cmd = 'show sdwan utd engine'
            dest_ip = self.topology.mgmt_ipaddr(device)
            output = self.confd_client.sendline(dest_ip, cmd)
            output = output['message']
            engine_status = '0'
            memory_status = '0'
            for line in output.split('\n'):
                if re.match(r'.*utd-oper-data.*', line):
                    if re.match(r'.*utd-engine-status memory-status.*', line):
                        line = line.split(' ')
                        memory_status = line[len(line) - 1]
                        memory_status = memory_status.replace('\r', '')
                        continue
                    if re.match(r'.*utd-engine-status status.*', line):
                        line = line.split(' ')
                        engine_status = line[len(line) - 1]
                        engine_status = engine_status.replace('\r', '')
                        continue
                else:
                    continue

            if engine_status == 'utd-oper-status-green' and memory_status == 'utd-oper-status-green':
                return [True, 'Engine is up and green']
            else:
                return [False, "Engine is down. Not green"]
        except Exception as ex:
                self.logger.error('Cannot verify engine status, Exception!!  %s' % ex)
                return [False, "Cannot verify engine status, Exception!!"]


    @run.test(['test_Appqoe_template_push'])
    def test_Appqoe_template_push(self):
        flag = 0
        pm_vedges = ['vm11']
        table_result = []
        Iteration = 1
        attachFail = []
        # ixL.load_ixia()
        # ixL.reassign_ports()
        for i in range(Iteration):
            for device in pm_vedges:
                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                version = self.test_show_version(device)
                print version
                table_result.append(['sdwan version: '+str(version[1]),''])
                table_result.append(['',''])
                self.logger.info('Clean up of existing policy/template configuration process is initiated')
                editStatus = self.test_edit_device_template_Remove_policies(device)
                if editStatus[0]:
                    table_result.append(['Test remove existing Security and Localized policy:' , 'PASS'])
                    self.logger.info('Test remove existing Security and Localized policy: PASSED')
                else:
                    table_result.append(['Test remove existing Security and Localized policy: ', 'FAIL'])
                    self.logger.info('Test remove existing Security and Localized policy: FAILED')
                    flag = flag + 1
                time.sleep(10)
            #***Detach template from devices if any *****
            self.logger.info('Detaching templates for Cedge')
            detach = self.test_detach_templates_from_devices(pm_vedges)
            if detach:
                table_result.append(['Test cEdge Detach Templates: ', 'PASS'])
                self.logger.info('Test cEdge Detach Templates is PASSED')
            else:
                table_result.append(['Test cEdge Detach Templates: ', 'FAIL'])
                self.logger.info('Test cEdge Detach Templates is FAILED')
                flag = flag + 1

            #*****detail to be given in yaml*********
            for device in pm_vedges:
                time.sleep(5)
                print(device)

                createResult = self.test_create_Device_template(device)
                if createResult[0]:
                    table_result.append(['Created Master templates ', 'PASS'])
                    self.logger.info('Create Master templates is PASSED')
                else:
                    table_result.append(['Failed to create Master templates: ', 'FAIL'])
                    self.logger.info('Failed to create Master templates is FAILED')
                    flag = flag + 1

                attachresult = self.test_Edit_And_Attach_Device_template(device)

                if attachresult[0]:
                    table_result.append(['Test Feature template Edit and Attach: ', 'PASS'])
                    self.logger.info('Test Feature template Edit and Attach is PASSED')
                else:
                    table_result.append(['Test Feature template Edit and Attach: ', 'FAIL'])
                    self.logger.info('Test Feature template Edit and Attach is FAILED')
                    attachFail.append(device)
                    flag = flag + 1
            #     time.sleep(180)
            #******** cli checks ***********

            for device in pm_vedges:
                self.logger.info('Starting Appqoe config Verification')
                appqoeresult = self.test_verify_Appqoe_configs_poll(device)

                if appqoeresult[0]:
                    table_result.append(['Appqoe SN status: Alive','PASS'])
                    self.logger.info('Appqoe SN status is PASSED')
                else:
                    table_result.append(['Appqoe SN status','FAIL'])
                    self.logger.info('Appqoe SN status: is FAILED')
                    flag = flag + 1
                # ixL.start_ix_traffic()
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

                appqoe_nat_stats = self.appqoe_nat_statistics(device)

                if appqoe_nat_stats[0]:
                    table_result.append(['Test Verify sdwan appqoe NAT stats: ', 'PASS'])
                    self.logger.info('Test Verify sdwan appqoe NAT stats is PASSED ')
                else:
                    table_result.append(['Test Verify sdwan appqoe NAT stats ', 'FAIL'])
                    self.logger.info('Test Verify sdwan appqoe NAT stats is FAILED ')
                    flag = flag + 1

                test_appqoe_libuinet = self.test_appqoe_libuinet_stats(device)

                if test_appqoe_libuinet[0]:
                    table_result.append(['Test Verify appqoe libuinet stats: ', 'PASS'])
                    self.logger.info('Test Verify appqoe libuinet stats is PASSED ')
                else:
                    table_result.append(['Test Verify appqoe libuinet stats ', 'FAIL'])
                    self.logger.info('Test Verify appqoe libuinet stats is FAILED ')
                    flag = flag + 1

                vrf = self.show_vrf_details(device)
                vrfvalue = vrf['1']
                test_appqoe_flows = self.verify_sdwan_appqoe_flows(device, vrfvalue=vrfvalue, server_port='80')

                if test_appqoe_flows[0]:
                    table_result.append(['Appqoe flows verification: ', 'PASS'])
                    self.logger.info('Appqoe flows verification is PASSED ')
                else:
                    table_result.append(['Appqoe flows verification ', 'FAIL'])
                    self.logger.info('Appqoe flows verification is FAILED ')
                    flag = flag + 1

                time.sleep(5)
                # ixL.stop_ixload_traffic()
                # ixL.cleanup_ix_traffic()
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
                            for eachcrash in data :
                                self.logger.info('core time :', eachcrash['core-time'])
                                self.logger.info('core filename :', eachcrash['core-filename'])
                                self.logger.info('core timedate :',eachcrash['core-time-date'])
                            flag = flag + 1
                except:
                    pass
                    self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))

        table.add_rows(table_result)
        print table.draw()
        if flag == 0:
            return [True,'Testcase executed successfully']
        else:
            return [False,'Few configs failed']
        # except:
        #     pass
        #     table.add_rows(table_result)
        #     print table.draw()
        #     self.logger.info('Caught an exception on running testcase during iteration: {}'.format(i))
        #     return [False,'Caught exception']

    @run.test(['test_Appqoe_SecuityPolicy'])
    def test_Appqoe_SecuityPolicy(self):
        flag = 0
        pm_vedges = ['pm9009']
        table_result = []
        Iteration = 1
        try:
            for i in range(Iteration):
                for device in pm_vedges:
                    table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                    version = self.test_show_version(device)
                    print version
                    table_result.append(['sdwan version: '+str(version[1]),''])
                    table_result.append(['',''])
                    self.logger.info('Clean up of existing policy/template configuration process is initiated')
                    editStatus = self.test_edit_device_template_Remove_policies(device)
                    if editStatus[0]:
                        table_result.append(['Test remove existing Security and Localized policy:' , 'PASS'])
                        self.logger.info('Test remove existing Security and Localized policy: PASSED')
                    else:
                        table_result.append(['Test remove existing Security and Localized policy: ', 'FAIL'])
                        self.logger.info('Test remove existing Security and Localized policy: FAILED')
                        flag = flag + 1
                    time.sleep(10)
                    system_ip = self.topology.system_ip(device)
                    #Get bfd sessions output before test
                    res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                    if res.status_code == 200:
                            time.sleep(5)
                            bfdSessionsUpbeforeReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                            self.logger.info('Bfd Sessions up before test: [%s]' % bfdSessionsUpbeforeReboot)
                            table_result.append(['Test BFD Sessions up before test: ', 'PASS'])
                    else:
                            table_result.append(['Test BFD Sessions up before test: ', 'FAIL'])
                        #Get omp peer check summary before test
                    res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                    if res.status_code == 200:
                            tlocSentbeforeReboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                            tlocRecievedbeforeReboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                            vSmartpeerbeforeReboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                            operStatebeforeReboot     =  json.loads(res.content)['data'][0]['operstate']
                            self.logger.info('tloc sent before test: [%s]' % tlocSentbeforeReboot)
                            self.logger.info('tloc sent before test: [%s]' % tlocRecievedbeforeReboot)
                            self.logger.info('tloc sent before test: [%s]' % vSmartpeerbeforeReboot)
                            self.logger.info('tloc sent before test: [%s]' % operStatebeforeReboot)
                            table_result.append(['Test OMP peer Sessions up before Reboot: ', 'PASS'])
                    else:
                            table_result.append(['Test OMP peer Sessions up before Reboot: ', 'FAIL'])
                #***Detach template from devices if any *****
                self.logger.info('Detaching templates for Cedge')
                detach = self.test_detach_templates_from_devices(pm_vedges)
                if detach:
                    table_result.append(['Test cEdge Detach Templates: ', 'PASS'])
                    self.logger.info('Test cEdge Detach Templates is PASSED')
                else:
                    table_result.append(['Test cEdge Detach Templates: ', 'FAIL'])
                    self.logger.info('Test cEdge Detach Templates is FAILED')
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
                    #pdb.set_trace()
                    time.sleep(5)

                    createResult = self.test_create_Device_template(device)
                    if createResult[0]:
                        table_result.append(['Created Master templates ', 'PASS'])
                        self.logger.info('Create Master templates is PASSED')
                    else:
                        table_result.append(['Failed to create Master templates: ', 'FAIL'])
                        self.logger.info('Failed to create Master templates is FAILED')
                        flag = flag + 1

                    attachresult = self.test_Edit_And_Attach_Device_template(device)
                    if attachresult[0]:
                        table_result.append(['Test Feature template Edit and Attach: ', 'PASS'])
                        self.logger.info('Test Feature template Edit and Attach is PASSED')
                    else:
                        table_result.append(['Test Feature template Edit and Attach: ', 'FAIL'])
                        self.logger.info('Test Feature template Edit and Attach is FAILED')
                        attachFail.append(device)
                        flag = flag + 1

                #Hardsleep for 3 min for CSR to get generated on device
                time.sleep(150)
                #******** cli checks ***********
                for device in pm_vedges:
                    self.logger.info('Starting TCP opt status Verification')
                    tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)

                    if tcp_opt_status[0]:
                        table_result.append(['TCP proxy running status: ', 'PASS'])
                        self.logger.info('TCP proxy running status is PASSED')
                    else:
                        table_result.append(['Test TCP proxy running status: ', 'FAIL'])
                        self.logger.info('Test TCP proxy running status is FAILED')
                        flag = flag + 1

                    #table.add_rows([['TCPOpt_Status','tcp_opt_status[0]']])
                    self.logger.info('Starting Appqoe config Verification')
                    appqoeresult = self.test_verify_Appqoe_configs_poll(device)

                    if appqoeresult[0]:
                        table_result.append(['Appqoe SN status: Alive','PASS'])
                        self.logger.info('Appqoe SN status is PASSED')
                    else:
                        table_result.append(['Appqoe SN status','FAIL'])
                        self.logger.info('Appqoe SN status: is FAILED')
                        flag = flag + 1

                    #table.add_rows([['Appqoe_Status','appqoeresult[0]']])
                    self.logger.info('Starting UTD config Verification')
                    utdresult = self.test_verify_UTD_configs_poll(device)

                    if utdresult[0]:
                        table_result.append(['UTD SN status Alive','PASS'])
                        self.logger.info('UTD SN status Alive is PASSED')
                    else:
                        table_result.append(['UTD SN status: ','FAIL'])
                        self.logger.info('UTD SN status is FAILED')
                        flag = flag + 1

                    self.logger.info('Starting trustpoint running status Verification')
                    trustpointstatus = self.test_verify_trustpoint_status(device)

                    if trustpointstatus[0]:
                        table_result.append(['Trustpoint PROXY-SIGNING-CA is configured: ', 'PASS'])
                        self.logger.info('Trustpoint PROXY-SIGNING-CA is configured PASSED')
                    else:
                        table_result.append(['Trustpoint PROXY-SIGNING-CA is not configured ', 'FAIL'])
                        self.logger.info('Trustpoint PROXY-SIGNING-CA is not configured is FAILED')
                        flag = flag + 1

                    self.logger.info('Starting utd running Verification')
                    utdstatus = self.test_UTDStatus(device)

                    if utdstatus[0]:
                        table_result.append(['UTD is in running status: ', 'PASS'])
                        self.logger.info('UTD is in running status and test is PASSED')
                    else:
                        table_result.append(['UTD is not in running status', 'FAIL'])
                        self.logger.info('Test UTD running status is FAILED')
                        flag = flag + 1

                    # pdb.set_trace()
                    IPScokets = self.test_verify_IP_Sockets(device)
                    if IPScokets[0]:
                        table_result.append(['IP sockets are available: ', 'PASS'])
                    else:
                        table_result.append(['IP sockets are not available: ', 'FAIL'])
                        flag = flag + 1

                    # sslProxyOpState = self.test_sslproxystats(device,'SSL Proxy Operational State','RUNNING')
                    #
                    # if sslProxyOpState[0]:
                    #     table_result.append(['SSlProxy operational state is running ', 'PASS'])
                    #     self.logger.info('SSlProxy operational state is running : PASSED')
                    # else:
                    #     table_result.append(['SSlProxy operational state is not running', 'FAIL'])
                    #     self.logger.info('SSlProxy operational state is not running is FAILED')
                    #     flag = flag + 1

                    # tcpProxyOpState = self.test_sslproxystats(device,'TCP Proxy Operational State','RUNNING')
                    #
                    # if tcpProxyOpState[0]:
                    #     table_result.append(['TCPProxy operational state is running ', 'PASS'])
                    #     self.logger.info('TCPProxy operational state is running : PASSED')
                    # else:
                    #     table_result.append(['TCPProxy operational state is not running', 'FAIL'])
                    #     self.logger.info('TCPProxy operational state is not running is FAILED')
                    #     flag = flag + 1

                    # CACertBundlefile = self.test_sslproxystats(device,'CA Cert Bundle','/bootflash/vmanage-admin/sslProxyDefaultCAbundle.pem')
                    #
                    # if CACertBundlefile[0]:
                    #     table_result.append(['Default CA cert bundle file is pushed ', 'PASS'])
                    #     self.logger.info('Default CA cert bundle file is pushed : PASSED')
                    # else:
                    #     table_result.append(['Default CA cert bundle file is not pushed', 'FAIL'])
                    #     self.logger.info('Default CA cert bundle file is not pushed is FAILED')
                    #     flag = flag + 1

                    self.logger.info('Starting TCP proxy statistics Verification:')
                    clear_tcp_proxy_statistics = self.test_clear_tcpProxy_Statistics(device)
                    if clear_tcp_proxy_statistics[0]:
                        table_result.append(['Test Clear TCP proxy statistics: ', 'PASS'])
                        self.logger.info('Test Clear TCP proxy statistics is PASSED')
                    else:
                        table_result.append(['Test Clear TCP proxy statistics: ', 'FAIL'])
                        self.logger.info('Test Clear TCP proxy statistics is FAILED')
                        flag = flag + 1

                    self.logger.info('Starting ssl proxy statistics Verification:')
                    ssl_proxy_statistics = self.test_SSLProxy_Statistics(device)

                    if ssl_proxy_statistics[0]:
                        table_result.append(['Test Verify SSL proxy statistics: ', 'PASS'])
                        self.logger.info('Test Verify TCP proxy statistics is PASSED')
                    else:
                        table_result.append(['Test Verify SSL proxy statistics: ', 'FAIL'])
                        self.logger.info('Test Verify SSL proxy statistics is FAILED')
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
                    # ixL.stop_ixload_traffic()
                    # ixL.cleanup_ix_traffic()
                    # table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                    # table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                    # table.add_rows(table_result)

                    system_ip = self.topology.system_ip(device)
                    #Get bfd sessions output after reboot
                    time.sleep(5)
                    try:
                        res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                        if res.status_code == 200:
                            bfdSessionsUpAfterReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                            self.logger.info('Bfd Sessions up after test: [%s]' % bfdSessionsUpAfterReboot)
                        if bfdSessionsUpAfterReboot != bfdSessionsUpbeforeReboot:
                            table_result.append(['Test BFD Sessions up after test: ', 'FAIL'])
                            self.logger.info('BFD session count did not match on iteration: {}'.format(i))
                            bfdSessionFlag.append(device)
                        else:
                            table_result.append(['Test BFD Sessions up after test: ', 'PASS'])
                    except:
                        pass
                        self.logger.info('Unable to fetch bfd summary on iteration: {}'.format(i))
                    #Get omp peer check summary after reboot
                    time.sleep(5)
                    try:
                        res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                        if res.status_code == 200:
                            tlocSentafterreboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                            tlocRecievedafterreboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                            vSmartpeerafterreboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                            operStateafterreboot     =  json.loads(res.content)['data'][0]['operstate']
                            self.logger.info('tloc sent after test: [%s]' % tlocSentafterreboot)
                            self.logger.info('tloc recieved after test: [%s]' % tlocRecievedafterreboot)
                            self.logger.info('vsmart peer  after test: [%s]' % vSmartpeerafterreboot)
                            self.logger.info('operstate after test: [%s]' % operStateafterreboot)
                        if tlocSentafterreboot != tlocSentbeforeReboot and tlocRecievedafterreboot != tlocRecievedbeforeReboot and vSmartpeerafterreboot != vSmartpeerbeforeReboot and operStatebeforeReboot != operStateafterreboot:
                            self.logger.info('OMP summary did not match on iteration: ')
                            table_result.append(['Test OMP peer Sessions up after test: ', 'FAIL'])
                            ompSessionFlag.append(device)
                        else:
                            table_result.append(['Test OMP peer Sessions up after test: ', 'PASS'])
                    except:
                        pass
                        self.logger.info('Unable to fetch OMP peer connection on iteration: {}'.format(i))
                    #verify crash log details from device
                    time.sleep(5)
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
                                for eachcrash in data :
                                    self.logger.info('core time :', eachcrash['core-time'])
                                    self.logger.info('core filename :', eachcrash['core-filename'])
                                    self.logger.info('core timedate :',eachcrash['core-time-date'])
                                flag = flag + 1
                    except:
                        pass
                        self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                    #verify any hardware errors in device
                    try:
                        hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                        if hardwareErrorres.status_code == 200:
                            self.logger.info('Fetching hardware errors')
                            data = json.loads(hardwareErrorres.content)['data']
                            if not data:
                                table_result.append(['Test Hardware errors: ', 'PASS'])
                                self.logger.info('Hardware errors are not seen')
                            else:
                                for eacherror in data :
                                    if eacherror['vdevice-host-name'] == device:
                                        table_result.append(['Test Hardware errors: ', 'FAIL'])
                                        self.logger.info('Hardware errors are seen on device [%s]' % device)
                                        self.logger.info('alarm-description:',eacherror['alarm-description'])
                                        self.logger.info('alarm-time:',eacherror['alarm-time'])
                                        self.logger.info('alarm-category:',eacherror['alarm-time'])
                                    else:
                                        table_result.append(['Test Hardware errors: ', 'PASS'])
                                        self.logger.info('Hardware errors are not seen on device [%s]' % device)
                                        flag = flag + 1
                    except:
                        pass
                        self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
            table.add_rows(table_result)
            print table.draw()
            if flag == 0:
                return [True,'Testcase executed successfully']
            else:
                return [False,'Few configs failed']
        except:
            pass
            table.add_rows(table_result)
            print table.draw()
            self.logger.info('Caught an exception on running testcase during iteration: {}'.format(i))
            return [False,'Caught exception']


    #@run.test(['Delete_Templates'])
    def Delete_Templates(self):
        """Get template id and delete existing vSmart templates"""
        flag = 0
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
                                self.logger.info('Test vSmart Delete existing Templates is PASSED')
                            else:
                                self.logger.info('Test vSmart Delete existing Templates is FAILED')
                                flag = flag + 1
        if flag == 0:
            return [True,'Deleted vSmart templates']
        else:
            return [False,'']

    @run.test(['Centralized_policy'])
    def Centralized_policy(self):
        flag = 0
        pm_vedges = ['vm11']
        table_result = []
        Iteration = 1
        BRRouter = 'vm11'
        DCRouter = 'vm10'
        try:
            for i in range(Iteration):
                #******Deactivate*****
                deactivate = self.test_deactivate_tcpOpt_dataPolicy()
                if deactivate:
                    table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'PASS'])
                    self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is PASSED')
                else:
                    table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'FAIL'])
                    self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is FAILED')
                    flag = flag + 1

                #***Detach templates for vSmart if any *****
                self.logger.info('Detaching templates for vSmart')
                detach = self.test_detach_templates_from_devices(vsmarts)
                if detach:
                    table_result.append(['Test vSmart Detach Template: ', 'PASS'])
                    self.logger.info('Test vSmart Detach Template is PASSED')
                else:
                    table_result.append(['Test vSmart Detach Template: ', 'FAIL'])
                    self.logger.info('Test vSmart Detach Template is FAILED')
                    flag = flag + 1

                #*****Delete templates **********
                time.sleep(5)
                delete = self.Delete_Templates()
                if delete:
                    table_result.append(['Test delete vSmart Template: ', 'PASS'])
                    self.logger.info('Test delete vSmart Template is PASSED')
                else:
                    table_result.append(['delete vSmart templates: ', 'FAIL'])
                    self.logger.info('delete vSmart templates is FAILED')
                    flag = flag + 1

                #*******Delete centralized policies *******
                deletePolicies = self.test_deletedatapolicy()
                self.logger.info('Deleting existing centralized policies:')
                if deletePolicies:
                    table_result.append(['Test Delete Centralized Data Policy:', 'PASS'])
                    self.logger.info('Test Delete Centralized Data Policy is PASSED')
                else:
                    table_result.append(['Test Delete Centralized Data Policy:', 'FAIL'])
                    self.logger.info('Test Delete Centralized Data Policy is FAILED')
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
                import pdb; pdb.set_trace()
                #*******create centralized policy*********
                self.logger.info('Creating datapolicy:')
                data_policy_create = self.test_create_centralized_Policy(BRRouter,DCRouter)
                import pdb; pdb.set_trace()
                if data_policy_create[0]:
                    table_result.append(['Test Create Centralized Data Policy: ', 'PASS'])
                    self.logger.info('Test Create Centralized Data Policy is PASSED')
                else:
                    table_result.append(['Test Create Centralized Data Policy: ', 'FAIL'])
                    self.logger.info('Test Create Centralized Data Policy is FAILED')
                    flag = flag + 1
                import pdb; pdb.set_trace()
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
                import pdb; pdb.set_trace()
                #******** cli checks ***********
                for device in pm_vedges:
                    self.logger.info('Starting TCP opt status Verification')
                    tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)

                    if tcp_opt_status[0]:
                        table_result.append(['TCP proxy running status: ', 'PASS'])
                        self.logger.info('TCP proxy running status is PASSED')
                    else:
                        table_result.append(['Test TCP proxy running status: ', 'FAIL'])
                        self.logger.info('Test TCP proxy running status is FAILED')
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
                    import pdb; pdb.set_trace()
                    self.logger.info('Starting Ixload Traffic Initialization')
                    client = AasthaClient(host='10.104.59.162')

                    test_id = client.run_test(cfg)
                    print("Started test {0}".format(test_id))

                    state = client.wait_until_test_finished(test_id)
                    print("Test {0} was finished with '{1}' state".format(test_id, state))

                    # ixL.reassign_ports()
                    # ixL.start_ix_traffic()
                    # self.logger.info('Traffic is running')
                    # time.sleep(60)
                    # table_result.append(['Test Ixload Traffic Start: ', 'PASS'])
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


                    #********  Stops the Traffic *****************
                    self.logger.info('Traffic stop and clean up process is initiated')
                    # ixL.stop_ixload_traffic()
                    # ixL.cleanup_ix_traffic()
                    # table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                    # table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                    # table.add_rows(table_result)


                    #verify crash log details from device
                    time.sleep(5)
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
                                for eachcrash in data :
                                    self.logger.info('core time :', eachcrash['core-time'])
                                    self.logger.info('core filename :', eachcrash['core-filename'])
                                    self.logger.info('core timedate :',eachcrash['core-time-date'])
                                flag = flag + 1
                    except:
                        pass
                        self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                    #verify any hardware errors in device
                    try:
                        hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                        if hardwareErrorres.status_code == 200:
                            self.logger.info('Fetching hardware errors')
                            data = json.loads(hardwareErrorres.content)['data']
                            if not data:
                                table_result.append(['Test Hardware errors: ', 'PASS'])
                                self.logger.info('Hardware errors are not seen')
                            else:
                                for eacherror in data :
                                    if eacherror['vdevice-host-name'] == device:
                                        table_result.append(['Test Hardware errors: ', 'FAIL'])
                                        self.logger.info('Hardware errors are seen on device [%s]' % device)
                                        self.logger.info('alarm-description:',eacherror['alarm-description'])
                                        self.logger.info('alarm-time:',eacherror['alarm-time'])
                                        self.logger.info('alarm-category:',eacherror['alarm-time'])
                                    else:
                                        table_result.append(['Test Hardware errors: ', 'PASS'])
                                        self.logger.info('Hardware errors are not seen on device [%s]' % device)
                                        flag = flag + 1
                    except:
                        pass
                        self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
            table.add_rows(table_result)
            print table.draw()
            if flag == 0:
                return [True,'Verified centralized policy']
            else:
                return [False,'Centralized policy Verification failed']
        except:
            pass
            table.add_rows(table_result)
            print table.draw()
            self.logger.info('Caught an exception on running testcase during iteration: {}'.format(i))
            return [False,'Centralized policy Verification failed with exception']

    @run.test(['Sanity_check'])
    def Sanity_check(self):
        flag = 0
        pm_vedges = ['vm10']
        table_result = []
        Iteration = 1
        BRRouter = 'vm10'
        DCRouter = 'vm11'
        attachFail     = []
        for i in range(Iteration):
            #***Detach template from devices if any *****
            self.logger.info('Detaching templates for Cedge')
            detach = self.test_detach_templates_from_devices(pm_vedges)
            if detach:
                table_result.append(['Test cEdge Detach Templates: ', 'PASS'])
                self.logger.info('Test cEdge Detach Templates is PASSED')
            else:
                table_result.append(['Test cEdge Detach Templates: ', 'FAIL'])
                self.logger.info('Test cEdge Detach Templates is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
            for device in pm_vedges:
                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                version = self.test_show_version(device)
                print version
                table_result.append(['sdwan version: '+str(version[1]),''])
                table_result.append(['',''])
                import pdb; pdb.set_trace()
                self.logger.info('Clean up of existing policy/template configuration process is initiated')
                editStatus = self.test_edit_device_template_Remove_policies(device)
                if editStatus[0]:
                    table_result.append(['Test remove existing Security and Localized policy:' , 'PASS'])
                    self.logger.info('Test remove existing Security and Localized policy: PASSED')
                else:
                    table_result.append(['Test remove existing Security and Localized policy: ', 'FAIL'])
                    self.logger.info('Test remove existing Security and Localized policy: FAILED')
                    flag = flag + 1
                time.sleep(10)
                system_ip = self.topology.system_ip(device)
                #Get bfd sessions output before test
                time.sleep(10)
                system_ip = self.topology.system_ip(device)
                res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                if res.status_code == 200:
                        time.sleep(5)
                        bfdSessionsUpbeforeReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                        self.logger.info('Bfd Sessions up before test: [%s]' % bfdSessionsUpbeforeReboot)
                else:
                        table_result.append(['Failed to fetch BFD Sessions before test: ', 'FAIL'])
                    #Get omp peer check summary before test
                res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                if res.status_code == 200:
                        tlocSentbeforeReboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                        tlocRecievedbeforeReboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                        vSmartpeerbeforeReboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                        operStatebeforeReboot     =  json.loads(res.content)['data'][0]['operstate']
                        self.logger.info('tloc sent before test: [%s]' % tlocSentbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % tlocRecievedbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % vSmartpeerbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % operStatebeforeReboot)

                else:
                        table_result.append(['Failed to fetch OMP peer Sessions before test: ', 'FAIL'])
            import pdb; pdb.set_trace()
            #****Delete localized policies ***********
            deleteLocalizedPolicy = self.test_delete_localizedPolicy()
            if deleteLocalizedPolicy:
                table_result.append(['Test Delete existing Localized policy: ', 'PASS'])
                self.logger.info('Localized policy is deleted')
            else:
                table_result.append(['Test Delete existing Localized policy: ', 'FAIL'])
                self.logger.info('Localized policy is not deleted')
                flag = flag + 1
            #******Clean up code for vSmart templates***********
            import pdb; pdb.set_trace()
            #***Deactivate*****
            # table_result.append(['Deactivate previos tcpOpt DataPolicy'])
            deactivate = self.test_deactivate_tcpOpt_dataPolicy()
            if deactivate:
                table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'PASS'])
                self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is PASSED')
            else:
                table_result.append(['Test vSmart Deactivate existing TcpOpt DataPolicy: ', 'FAIL'])
                self.logger.info('Test vSmart Deactivate existing TcpOpt DataPolicy is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
            #***Detach templates for vSmart if any *****
            self.logger.info('Detaching templates for vSmart')
            detach = self.test_detach_templates_from_devices(vsmarts)
            if detach:
                table_result.append(['Test vSmart Detach Template: ', 'PASS'])
                self.logger.info('Test vSmart Detach Template is PASSED')
            else:
                table_result.append(['Test vSmart Detach Template: ', 'FAIL'])
                self.logger.info('Test vSmart Detach Template is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
            #*****Delete templates **********
            delete = self.Delete_Templates()
            if delete:
                table_result.append(['Test delete vSmart Template: ', 'PASS'])
                self.logger.info('Test delete vSmart Template is PASSED')
            else:
                table_result.append(['delete vSmart templates: ', 'FAIL'])
                self.logger.info('delete vSmart templates is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
            #*******Delete centralized policies *******
            deletePolicies = self.test_deletedatapolicy()
            self.logger.info('Deleting existing centralized policies:')
            if deletePolicies:
                table_result.append(['Test Delete Centralized Data Policy:', 'PASS'])
                self.logger.info('Test Delete Centralized Data Policy is PASSED')
            else:
                table_result.append(['Test Delete Centralized Data Policy:', 'FAIL'])
                self.logger.info('Test Delete Centralized Data Policy is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
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
            import pdb; pdb.set_trace()
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
            import pdb; pdb.set_trace()
            #*******create centralized policy*********
            self.logger.info('Creating datapolicy:')
            data_policy_create = self.test_create_centralized_Policy(BRRouter,DCRouter)
            if data_policy_create[0]:
                table_result.append(['Test Create Centralized Data Policy: ', 'PASS'])
                self.logger.info('Test Create Centralized Data Policy is PASSED')
            else:
                table_result.append(['Test Create Centralized Data Policy: ', 'FAIL'])
                self.logger.info('Test Create Centralized Data Policy is FAILED')
                flag = flag + 1
            import pdb; pdb.set_trace()
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
            import pdb; pdb.set_trace()
            #*******create localized policy*********
            self.logger.info('******** Creating localized policy:')
            localized_policy_create = self.test_localizedPolicy(BRRouter,DCRouter)
            if localized_policy_create:
                table_result.append(['Test Create localized Data Policy: ', 'PASS'])
                self.logger.info('******** Localized Data Policy created successfully')
            else:
                table_result.append(['Test Create localized Data Policy: ', 'FAIL'])
                self.logger.info('******** Localized Device failed to create Data Policy')
                flag = flag + 1

            import pdb; pdb.set_trace()
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
            import pdb; pdb.set_trace()
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
            import pdb; pdb.set_trace()
            self.logger.info('Edit the device template and attach the security/appqoe/localizedpolicy/nbar/fnf')
            #*****detail to be given in yaml*********
            for device in pm_vedges:
                #pdb.set_trace()
                time.sleep(5)
                print(device)
                createResult = self.test_create_Device_template(device)
                if createResult[0]:
                    table_result.append(['Created Master templates ', 'PASS'])
                    self.logger.info('Create Master templates is PASSED')
                else:
                    table_result.append(['Failed to create Master templates: ', 'FAIL'])
                    self.logger.info('Failed to create Master templates is FAILED')
                    flag = flag + 1
                import pdb; pdb.set_trace()
                attachresult = self.test_Edit_And_Attach_Device_template(device)
                if attachresult[0]:
                    table_result.append(['Test Feature template Edit and Attach: ', 'PASS'])
                    self.logger.info('Test Feature template Edit and Attach is PASSED')
                else:
                    table_result.append(['Test Feature template Edit and Attach: ', 'FAIL'])
                    self.logger.info('Test Feature template Edit and Attach is FAILED')
                    attachFail.append(device)
                    flag = flag + 1

            # Hardsleep for 3 min for CSR to get generated on device
            time.sleep(150)
            import pdb; pdb.set_trace()
            #******** cli checks ***********
            for device in pm_vedges:
                self.logger.info('Starting TCP opt status Verification')
                tcp_opt_status = self.test_sdwan_appqoe_tcpopt_status(device)

                if tcp_opt_status[0]:
                    table_result.append(['TCP proxy running status: ', 'PASS'])
                    self.logger.info('TCP proxy running status is PASSED')
                else:
                    table_result.append(['Test TCP proxy running status: ', 'FAIL'])
                    self.logger.info('Test TCP proxy running status is FAILED')
                    flag = flag + 1


                #table.add_rows([['TCPOpt_Status','tcp_opt_status[0]']])
                self.logger.info('Starting Appqoe config Verification')
                appqoeresult = self.test_verify_Appqoe_configs_poll(device)

                if appqoeresult[0]:
                    table_result.append(['Appqoe SN status: Alive','PASS'])
                    self.logger.info('Appqoe SN status is PASSED')
                else:
                    table_result.append(['Appqoe SN status','FAIL'])
                    self.logger.info('Appqoe SN status: is FAILED')
                    flag = flag + 1

                #table.add_rows([['Appqoe_Status','appqoeresult[0]']])
                self.logger.info('Starting UTD config Verification')
                utdresult = self.test_verify_UTD_configs_poll(device)

                if utdresult[0]:
                    table_result.append(['UTD SN status Alive','PASS'])
                    self.logger.info('UTD SN status Alive is PASSED')
                else:
                    table_result.append(['UTD SN status: ','FAIL'])
                    self.logger.info('UTD SN status is FAILED')
                    flag = flag + 1

                self.logger.info('Starting trustpoint running status Verification')
                trustpointstatus = self.test_verify_trustpoint_status(device)

                if trustpointstatus[0]:
                    table_result.append(['Trustpoint PROXY-SIGNING-CA is configured: ', 'PASS'])
                    self.logger.info('Trustpoint PROXY-SIGNING-CA is configured PASSED')
                else:
                    table_result.append(['Trustpoint PROXY-SIGNING-CA is not configured ', 'FAIL'])
                    self.logger.info('Trustpoint PROXY-SIGNING-CA is not configured is FAILED')
                    flag = flag + 1

                self.logger.info('Starting utd running Verification')
                utdstatus = self.test_UTDStatus(device)

                if utdstatus[0]:
                    table_result.append(['UTD is in running status: ', 'PASS'])
                    self.logger.info('UTD is in running status and test is PASSED')
                else:
                    table_result.append(['UTD is not in running status', 'FAIL'])
                    self.logger.info('Test UTD running status is FAILED')
                    flag = flag + 1

                # pdb.set_trace()
                IPScokets = self.test_verify_IP_Sockets(device)
                if IPScokets[0]:
                    table_result.append(['IP sockets are available: ', 'PASS'])
                else:
                    table_result.append(['IP sockets are not available: ', 'FAIL'])
                    flag = flag + 1
                sslProxyOpState = self.test_sslproxystats(device,'SSL Proxy Operational State','RUNNING')
                import pdb; pdb.set_trace()

                if sslProxyOpState[0]:
                    table_result.append(['SSlProxy operational state is running ', 'PASS'])
                    self.logger.info('SSlProxy operational state is running : PASSED')
                else:
                    table_result.append(['SSlProxy operational state is not running', 'FAIL'])
                    self.logger.info('SSlProxy operational state is not running is FAILED')
                    flag = flag + 1

                tcpProxyOpState = self.test_sslproxystats(device,'TCP Proxy Operational State','RUNNING')

                if tcpProxyOpState[0]:
                    table_result.append(['TCPProxy operational state is running ', 'PASS'])
                    self.logger.info('TCPProxy operational state is running : PASSED')
                else:
                    table_result.append(['TCPProxy operational state is not running', 'FAIL'])
                    self.logger.info('TCPProxy operational state is not running is FAILED')
                    flag = flag + 1

                CACertBundlefile = self.test_sslproxystats(device,'CA Cert Bundle','/bootflash/vmanage-admin/sslProxyDefaultCAbundle.pem')

                if CACertBundlefile[0]:
                    table_result.append(['Default CA cert bundle file is pushed ', 'PASS'])
                    self.logger.info('Default CA cert bundle file is pushed : PASSED')
                else:
                    table_result.append(['Default CA cert bundle file is not pushed', 'FAIL'])
                    self.logger.info('Default CA cert bundle file is not pushed is FAILED')
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
                # self.logger.info('Starting Ixload Traffic Initialization')
                # ixL.reassign_ports()
                # ixL.start_ix_traffic()
                # self.logger.info('Traffic is running')
                # time.sleep(60)
                # table_result.append(['Test Ixload Traffic Start: ', 'PASS'])
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
                # ixL.stop_ixload_traffic()
                # ixL.cleanup_ix_traffic()
                # table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                # table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                # table.add_rows(table_result)

                system_ip = self.topology.system_ip(device)
                #Get bfd sessions output after reboot
                time.sleep(5)
                try:
                    res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        bfdSessionsUpAfterReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                        self.logger.info('Bfd Sessions up after test: [%s]' % bfdSessionsUpAfterReboot)
                    if bfdSessionsUpAfterReboot != bfdSessionsUpbeforeReboot:
                        table_result.append(['BFD Sessions did not match: ', 'FAIL'])
                        self.logger.info('BFD session count did not match on iteration: {}'.format(i))
                    else:
                        table_result.append(['BFD Sessions matched: ', 'PASS'])
                except:
                    pass
                    table_result.append(['Exception raised while fetching BFD Sessions: ', 'PASS'])
                    self.logger.info('Unable to fetch bfd summary on iteration: {}'.format(i))
                #Get omp peer check summary after reboot
                time.sleep(5)
                try:
                    res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        tlocSentafterreboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                        tlocRecievedafterreboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                        vSmartpeerafterreboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                        operStateafterreboot     =  json.loads(res.content)['data'][0]['operstate']
                        self.logger.info('tloc sent after test: [%s]' % tlocSentafterreboot)
                        self.logger.info('tloc recieved after test: [%s]' % tlocRecievedafterreboot)
                        self.logger.info('vsmart peer  after test: [%s]' % vSmartpeerafterreboot)
                        self.logger.info('operstate after test: [%s]' % operStateafterreboot)
                    if tlocSentafterreboot != tlocSentbeforeReboot and tlocRecievedafterreboot != tlocRecievedbeforeReboot and vSmartpeerafterreboot != vSmartpeerbeforeReboot and operStatebeforeReboot != operStateafterreboot:
                        self.logger.info('OMP summary did not match on iteration: ')
                        table_result.append(['OMP sessions did not matched: ', 'FAIL'])
                    else:
                        table_result.append(['OMP session matched', 'PASS'])
                except:
                    pass
                    table_result.append(['Caught exception while fetching OMP sessions', 'FAIL'])
                    self.logger.info('Unable to fetch OMP peer connection on iteration: {}'.format(i))
                #verify crash log details from device
                time.sleep(5)
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
                            for eachcrash in data :
                                self.logger.info('core time :', eachcrash['core-time'])
                                self.logger.info('core filename :', eachcrash['core-filename'])
                                self.logger.info('core timedate :',eachcrash['core-time-date'])
                            flag = flag + 1
                except:
                    pass
                    self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                #verify any hardware errors in device
                try:
                    hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                    if hardwareErrorres.status_code == 200:
                        self.logger.info('Fetching hardware errors')
                        data = json.loads(hardwareErrorres.content)['data']
                        if not data:
                            table_result.append(['Test Hardware errors: ', 'PASS'])
                            self.logger.info('Hardware errors are not seen')
                        else:
                            for eacherror in data :
                                if eacherror['vdevice-host-name'] == device:
                                    table_result.append(['Test Hardware errors: ', 'FAIL'])
                                    self.logger.info('Hardware errors are seen on device [%s]' % device)
                                    self.logger.info('alarm-description:',eacherror['alarm-description'])
                                    self.logger.info('alarm-time:',eacherror['alarm-time'])
                                    self.logger.info('alarm-category:',eacherror['alarm-time'])
                                else:
                                    table_result.append(['Test Hardware errors: ', 'PASS'])
                                    self.logger.info('Hardware errors are not seen on device [%s]' % device)
                                    flag = flag + 1
                except:
                    pass
                    self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
        table.add_rows(table_result)
        print table.draw()
        if flag == 0:
            return [True,'Sanity case executed successfully']
        else:
            return [False,'Sanity case executed but failed']
        # except:
        #     pass
        #     table.add_rows(table_result)
        #     print table.draw()
        #     self.logger.info('Sanity case caught exception and failed during iteration: {}'.format(i))
        #     return [False,'Sanity case caught exception and failed']

    @run.test(['LocalizedPolicy'])
    def LocalizedPolicy(self):
        flag = 0
        pm_vedges = ['pm9009']
        table_result = []
        Iteration = 1
        BRRouter = 'pm9009'
        DCRouter = 'pm9010'

        # try:
        for i in range(Iteration):
            for device in pm_vedges:
                table_result.append(['RESULT SUMMARY FOR: '+str(device),'ITERATION: '+str(i)])
                version = self.test_show_version(device)
                print version
                table_result.append(['sdwan version: '+str(version[1]),''])
                table_result.append(['',''])
                self.logger.info('Clean up of existing policy/template configuration process is initiated')
                editStatus = self.test_edit_device_template_Remove_policies(device)
                if editStatus[0]:
                    table_result.append(['Test remove existing Security and Localized policy:' , 'PASS'])
                    self.logger.info('Test remove existing Security and Localized policy: PASSED')
                else:
                    table_result.append(['Test remove existing Security and Localized policy: ', 'FAIL'])
                    self.logger.info('Test remove existing Security and Localized policy: FAILED')
                    flag = flag + 1
                #Get bfd sessions output before test
                time.sleep(10)
                system_ip = self.topology.system_ip(device)
                res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                if res.status_code == 200:
                        time.sleep(5)
                        bfdSessionsUpbeforeReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                        self.logger.info('Bfd Sessions up before test: [%s]' % bfdSessionsUpbeforeReboot)
                else:
                        table_result.append(['Failed to fetch BFD Sessions before test: ', 'FAIL'])
                    #Get omp peer check summary before test
                res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                if res.status_code == 200:
                        tlocSentbeforeReboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                        tlocRecievedbeforeReboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                        vSmartpeerbeforeReboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                        operStatebeforeReboot     =  json.loads(res.content)['data'][0]['operstate']
                        self.logger.info('tloc sent before test: [%s]' % tlocSentbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % tlocRecievedbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % vSmartpeerbeforeReboot)
                        self.logger.info('tloc sent before test: [%s]' % operStatebeforeReboot)

                else:
                        table_result.append(['Failed to fetch OMP peer Sessions before test: ', 'FAIL'])
            #***Detach template from devices if any *****
            self.logger.info('Detaching templates for Cedge')
            detach = self.test_detach_templates_from_devices(pm_vedges)
            if detach:
                table_result.append(['Test cEdge Detach Templates: ', 'PASS'])
                self.logger.info('Test cEdge Detach Templates is PASSED')
            else:
                table_result.append(['Test cEdge Detach Templates: ', 'FAIL'])
                self.logger.info('Test cEdge Detach Templates is FAILED')
                flag = flag + 1

            #****Delete localized policies ***********
            deleteLocalizedPolicy = self.test_delete_localizedPolicy()
            if deleteLocalizedPolicy:
                table_result.append(['Test Delete existing Localized policy: ', 'PASS'])
                self.logger.info('Localized policy is deleted')
            else:
                table_result.append(['Test Delete existing Localized policy: ', 'FAIL'])
                self.logger.info('Localized policy is not deleted')
                flag = flag + 1

            #*******create localized policy*********
            self.logger.info('******** Creating localized policy:')
            localized_policy_create = self.test_localizedPolicy(BRRouter,DCRouter)
            if localized_policy_create:
                table_result.append(['Test Create localized Data Policy: ', 'PASS'])
                self.logger.info('******** Localized Data Policy created successfully')
            else:
                table_result.append(['Test Create localized Data Policy: ', 'FAIL'])
                self.logger.info('******** Localized Device failed to create Data Policy')
                flag = flag + 1


            self.logger.info('Edit the device template and attach the security/appqoe/localizedpolicy/nbar/fnf')
            #*****detail to be given in yaml*********
            for device in pm_vedges:
                #pdb.set_trace()
                time.sleep(5)
                createResult = self.test_create_Device_template(device)
                if createResult[0]:
                    table_result.append(['Created Master templates ', 'PASS'])
                    self.logger.info('Create Master templates is PASSED')
                else:
                    table_result.append(['Failed to create Master templates: ', 'FAIL'])
                    self.logger.info('Failed to create Master templates is FAILED')
                    flag = flag + 1

                applyQOS = self.test_apply_QOS_on_LANInterface(device,0,0)
                if applyQOS[0]:
                    table_result.append(['Applied QOS to interfaces ', 'PASS'])
                    self.logger.info('Applied QOS to interfaces is PASSED')
                else:
                    table_result.append(['Failed to apply QOS to interfaces ', 'FAIL'])
                    self.logger.info('apply QOS to interfaces is FAILED')

                attachresult = self.test_Edit_And_Attach_Device_template(device)
                if attachresult[0]:
                    table_result.append(['Test Feature template Edit and Attach: ', 'PASS'])
                    self.logger.info('Test Feature template Edit and Attach is PASSED')
                else:
                    table_result.append(['Test Feature template Edit and Attach: ', 'FAIL'])
                    self.logger.info('Test Feature template Edit and Attach is FAILED')
                    flag = flag + 1

            #******** cli checks ***********
            for device in pm_vedges:

                self.logger.info('Starting Hubspoke verification')
                hubspoke = self.hubSpokeCheck(device)

                if hubspoke[0]:
                    table_result.append(['Hubspoke config is established', 'PASS'])
                    self.logger.info('Hubspoke configs are pushed to device is PASSED')
                else:
                    table_result.append(['Hubspoke config is not established: ', 'FAIL'])
                    self.logger.info('Hubspoke config is not established is FAILED')
                    flag = flag + 1

                #********  Starts the Traffic *****************
                # self.logger.info('Starting Ixload Traffic Initialization')
                # ixL.reassign_ports()
                # ixL.start_ix_traffic()
                # self.logger.info('Traffic is running')
                # time.sleep(60)
                # table_result.append(['Test Ixload Traffic Start: ', 'PASS'])
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

                #********  Stops the Traffic *****************
                self.logger.info('Traffic stop and clean up process is initiated')
                # ixL.stop_ixload_traffic()
                # ixL.cleanup_ix_traffic()
                # table_result.append(['Test Ixload Traffic Cleanup: ', 'PASS'])
                # table_result.append(['Test Ixload Traffic Stop: ', 'PASS'])
                # table.add_rows(table_result)

                system_ip = self.topology.system_ip(device)
                #Get bfd sessions output after reboot
                time.sleep(5)
                try:
                    res = vman_session.maint.dev_reboot.get_bfd_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        bfdSessionsUpAfterReboot = json.loads(res.content)['data'][0]['bfd-sessions-up']
                        self.logger.info('Bfd Sessions up after test: [%s]' % bfdSessionsUpAfterReboot)
                    if bfdSessionsUpAfterReboot != bfdSessionsUpbeforeReboot:
                        table_result.append(['BFD Sessions did not match: ', 'FAIL'])
                        self.logger.info('BFD session count did not match on iteration: {}'.format(i))
                    else:
                        table_result.append(['BFD Sessions matched: ', 'PASS'])
                except:
                    pass
                    table_result.append(['Exception raised while fetching BFD Sessions: ', 'PASS'])
                    self.logger.info('Unable to fetch bfd summary on iteration: {}'.format(i))
                #Get omp peer check summary after reboot
                time.sleep(5)
                try:
                    res = vman_session.maint.dev_reboot.get_omp_summary(profile, None,system_ip)
                    if res.status_code == 200:
                        tlocSentafterreboot      =  json.loads(res.content)['data'][0]['tlocs-sent']
                        tlocRecievedafterreboot  =  json.loads(res.content)['data'][0]['tlocs-received']
                        vSmartpeerafterreboot    =  json.loads(res.content)['data'][0]['vsmart-peers']
                        operStateafterreboot     =  json.loads(res.content)['data'][0]['operstate']
                        self.logger.info('tloc sent after test: [%s]' % tlocSentafterreboot)
                        self.logger.info('tloc recieved after test: [%s]' % tlocRecievedafterreboot)
                        self.logger.info('vsmart peer  after test: [%s]' % vSmartpeerafterreboot)
                        self.logger.info('operstate after test: [%s]' % operStateafterreboot)
                    if tlocSentafterreboot != tlocSentbeforeReboot and tlocRecievedafterreboot != tlocRecievedbeforeReboot and vSmartpeerafterreboot != vSmartpeerbeforeReboot and operStatebeforeReboot != operStateafterreboot:
                        self.logger.info('OMP summary did not match on iteration: ')
                        table_result.append(['OMP sessions did not matched: ', 'FAIL'])
                    else:
                        table_result.append(['OMP session matched', 'PASS'])
                except:
                    pass
                    table_result.append(['Caught exception while fetching OMP sessions', 'FAIL'])
                    self.logger.info('Unable to fetch OMP peer connection on iteration: {}'.format(i))
                #verify crash log details from device
                time.sleep(5)
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
                    table_result.append(['Caught exception on fetching crash log ', 'FAIL'])
                    self.logger.info('Caught an exception on fetching crash log for iteration: {}'.format(i))
                #verify any hardware errors in device
                try:
                    hardwareErrorres = vman_session.dashboard.get_device_Hardware_errors(profile, None)
                    if hardwareErrorres.status_code == 200:
                        self.logger.info('Fetching hardware errors')
                        data = json.loads(hardwareErrorres.content)['data']
                        if not data:
                            table_result.append(['Test Hardware errors: ', 'PASS'])
                            self.logger.info('Hardware errors are not seen')
                        else:
                            for eacherror in data :
                                if eacherror['vdevice-host-name'] == device:
                                    table_result.append(['Test Hardware errors: ', 'FAIL'])
                                    self.logger.info('Hardware errors are seen on device [%s]' % device)
                                    self.logger.info('alarm-description:',eacherror['alarm-description'])
                                    self.logger.info('alarm-time:',eacherror['alarm-time'])
                                    self.logger.info('alarm-category:',eacherror['alarm-time'])
                                else:
                                    table_result.append(['Test Hardware errors: ', 'PASS'])
                                    self.logger.info('Hardware errors are not seen on device [%s]' % device)
                                    flag = flag + 1
                except:
                    pass
                    table_result.append(['Caught an exception on fetching hardware errors ', 'FAIL'])
                    self.logger.info('Caught an exception on fetching hardware errors on iteration: {}'.format(i))
        table.add_rows(table_result)
        print table.draw()
        if flag == 0:
            return [True,'Localized policy verification is success']
        else:
            return [False,'Localized policy verification failed']
        # except:
        #     pass
        #     table.add_rows(table_result)
        #     print table.draw()
        #     self.logger.info('Caught an exception on running Localized policy testcase during iteration: {}'.format(i))
        #     return [False,'Caught an exception on running Localized policy testcase']


    # @run.test(['fnf_drop_check'])
    def fnf_drop_check(self,device):
        cmd="sh sdwan app-fwd cflowd flows  | inc drop"
        #pdb.set_trace()
        #cmd = "sh sdwan app-fwd cflowd flows | tee bootflash:Test1"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        drop_list = []
        for line in output.split('\n'):
            if re.match(r'.*drop-cause.*', line):
                line = line.split(' ')
                drop_cause = line[len(line) - 1]
                drop_cause = drop_cause.replace('\r', '')
                if drop_cause == 'No Drop':
                    continue
                else:
                    drop_list.append(drop_cause)
        if range(len(drop_list)) > 0:
            return[True,'']
        else:
            return[False,'']


    # @run.test(['fnf_egress'])
    def fnf_egress(self,device='pm9009', srcip = '192.168.1.2', dstip = '208.67.220.220', exp_op = ''):
        cmd="show sdwan app-fwd cflowd flows format table"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0",timeout=600)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        if len(output) == 0 | len(srcip) == 0 | len(dstip) == 0:
            print("Empty value passed in show output or in srcip or in dstip")
            return [False, []]
        else:
            temp = output.split("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

            #temp = output.split("-")
            if len(temp[1]) == 0:

                print("No flow values available as part of show output")
                return [False, []]
            else:
                egress_list = []
                val = temp[-1].strip()
                flow_values = val.split("\n")

                for i in range(len(flow_values)):
                    get = flow_values[i].split()
                    print(get)
                    if get:
                        if device in get[0]:
                            break;
                        if (get[1] == srcip) & (get[2] == dstip):
                            egress_list.append(get[16])
                if len(egress_list) == 0:
                    print("No Valid egress interface available for given srcip and dstip combination")
                    return [False, []]
                elif len(set(egress_list)) > 1:
                    print("More than one egress interface present for given srcip and dstip, Suspecting Assymetric Routing")
                    return [False, list(set(egress_list))]
                else:
                    if len(exp_op) == 0:
                        print("Egress interface to be validated is not provided , returning egress interface from flows")
                        return [True, list(set(egress_list))]
                    else:
                        if egress_list[0] == exp_op:
                            print("Found expected Egress Interface in the Flows")
                            return [True, list(set(egress_list))]
                        else:
                            print("expected Egress Interface in the Flows is NotFound")
                            return [False, list(set(egress_list))]

    #@run.test(['qos_stats'])
    def qos_stats(self, device, interface=[]):
        for i in range(len(interface)):
            flag = 0
            cmd = 'show policy-map interface '+str(interface[i])
            dest_ip = self.topology.mgmt_ipaddr(device)
            output2 = self.confd_client.sendline(dest_ip, cmd)
            output2 = output2['message']
            resultdict1 = dict()
            REGEX_LST1 = [
                ('ClassMap',        re.compile(".*Class-map: +(?P<ClassMap>.*) \(match-any\)")),
                ('PKT_DET',              re.compile("(?P<Packets>.*) +packets, +(?P<Bytes>[0-9]+) +bytes$")),
                ('DROP_DET',              re.compile(".*5 minute offered rate (?P<rate>[0-9]+) +bps, +drop rate (?P<bps>[0-9]+) +bps.*"))
            ]
            REGEX1 = OrderedDict(REGEX_LST1)
            output3 = output2.splitlines()
            if not output3:
                print resultdict1
            for line in output3:
                regex, match_obj = self.get_match(REGEX1, line)
                if not match_obj:
                    continue
                if regex in ('ClassMap', 'PKT_DET','DROP_DET'):
                    for i,j in match_obj.groupdict().items():
                        try:
                            resultdict1[i].append(j)
                        except:
                            resultdict1[i]=[j]

            if resultdict1['Packets'][resultdict1['ClassMap'].index('Queue0')] != 0:
                self.logger.info('Packets count got increased')
            else:
                self.logger.info('Packets are zero')
                return [False,'Packets are zero']
            if resultdict1['Bytes'][resultdict1['ClassMap'].index('Queue0')] != 0:
                self.logger.info('Bytes count got increased')
            else:
                self.logger.info('Bytes are zero')
                return [False,'Bytes are zero']
            if resultdict1['rate'][resultdict1['ClassMap'].index('Queue0')] != 0:
                  self.logger.info('Rates count got increased')
            else:
                self.logger.info('Rates are zero')
                return [False,'Rates are zero']
            print(resultdict1['bps'][resultdict1['ClassMap'].index('Queue0')])
            if resultdict1['bps'][resultdict1['ClassMap'].index('Queue0')] == '0000':
                self.logger.info('BPS is zero')
            else:
                self.logger.info('BPS is not zero')
                return [False,'BPS is not zero']
        return [True, 'QOS is as expected']



    # @run.test(['fnf_drop'])
    def fnf_drop(self,device='pm9009'):
        cmd="show sdwan app-fwd cflowd flows format table"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0",timeout=300)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        if len(output) == 0:
            print("Empty value passed as part of show output")
            return [False, '']
        else:
            #pdb.set_trace()
            temp = output.split("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
            print(temp[-1])
            if len(temp[-1]) == 0:
                print("No flow values available as part of show output")
                return [False, []]
            else:
                drop_list = []
                val = temp[1].strip()
                flow_values = val.split("\n")
                for i in range(len(flow_values)):
                    get = flow_values[i].split()
                    if (get[20] != 'No') | (get[21] != 'Drop'):
                        drop_list.append(flow_values[i])
                if len(drop_list) == 0:
                    print("No drops seen in the flows")
                    return [True, []]
                else:
                    print("Drops seen as part of flows")
                    return [False, drop_list]

    def test_appqoe_libuinet_stats(self, device):
        flag = 0
        cmd = 'show sdwan appqoe libuinet-statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0",timeout=300)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        # print output
        parsed_output = output.split('\n')
        parsed_output = [string.strip() for string in parsed_output if (string != "" and re.match(r'.*:.*', string))]
        sppi_stats_index = parsed_output.index('SPPI Statistics:')
        vpath_stats_index = parsed_output.index('Vpath Statistics:')
        sppi_stats = {}
        vpath_stats = {}
        for line in parsed_output[sppi_stats_index+1:vpath_stats_index]:
            self.key_value_dict_str(line, sppi_stats)
        for line in parsed_output[vpath_stats_index+1:]:
            self.key_value_dict_str(line, vpath_stats)
        appqoe_libuinet_stats = sppi_stats, vpath_stats
        if vpath_stats['Packets In'] == 0:
            flag = flag + 1
        else:
            self.logger.info(vpath_stats['Packets In'])
        if vpath_stats['IP Input Packets'] == 0:
            flag = flag + 1
        else:
            self.logger.info(vpath_stats['IP Input Packets'])
        if vpath_stats['IP Output Packets'] == 0:
            flag = flag + 1
        else:
            self.logger.info(vpath_stats['IP Output Packets'])
        if flag == 0:
            return [True,'appqoe libuinet-statistics are proper']
        else:
            return [False,'appqoe libuinet-statistics are not proper']

    def appqoe_nat_statistics(self, device):
        cmd = 'show sdwan appqoe nat-statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0",timeout=300)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        flag = 0
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        if result['Port Alloc Failures'] == 0:
            self.logger.info('Port Alloc Failures is zero')
        else:
            flag = flag + 1
        if result['Port Free Failures'] == 0:
            self.logger.info('Port Free Failures is zero')
        else:
            flag = flag + 1
        if result['Insert Success'] > 0:
            self.logger.info('Insert Success is greater than zero')
        else:
            flag = flag + 1
        if result['Delete Success'] > 0:
            self.logger.info('Delete Success is greater than zero')
        else:
            flag = flag + 1
        if flag == 0:
            return [True, 'Appqoe nat-statistics are proper']
        else:
            return [False, 'Appqoe nat-statistics are not proper']


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

    def show_vrf_details(self,device):
        cmd="show vrf detail | inc VRF Id"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = re.findall("VRF\s\d+\s\WVRF\sId\s\W\s\d+", output)
        vrf=[]
        vpn=[]
        for line in result:
            word = line.split('(')
            vrf.append(word[0].strip('VRF '))
            vpn.append(word[1].strip('VRF Id = '))
        vrf = dict(zip(vrf,vpn))
        return vrf

    # @run.test(['verify_sdwan_appqoe_flows'])
    def verify_sdwan_appqoe_flows(self,device, vrfvalue, server_port):
        cmd = 'show sdwan appqoe flow vpn-id {} server-port {}'.format(str(vrfvalue), server_port)
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0",timeout=300)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        flag = 0
        for line in output.split('\n'):
            if 'No Matching Flows' in line:
                return [False,'No matching flows found']
            regex = re.search(r'[0-9]+\s([0-9]+)\s+([0-9.]+)[:0-9]+\s+([0-9.:]+)', line)
            if regex:
                if regex.group(1) == vrfvalue:
                    pass
                else:
                    flag = flag + 1
        if flag == 0:
            return [True,'Matching Flows found']
        else:
            return [False,'No Matching Flows found']

    def get_config(self,res):
        data = res.content
        data = json.loads(data)
        data = data['config']
        return data

if __name__ == '__main__':
    import pdb; pdb.set_trace()
    run.call_all(appqoe_system)

# QOSToBeApplied = [self.config['machines'][device]['service_side_intf']['intf'][0]]
#                     self.logger.info('Starting QOS Verification:')
#                     qos_verify = self.qos_stats(device,QOSToBeApplied)

#                     if qos_verify[0]:
#                         table_result.append(['Test Verify TCP proxy statistics: ', 'PASS'])
#                         self.logger.info('Test Verify TCP proxy statistics is PASSED')
#                     else:
#                         table_result.append(['Test Verify TCP proxy statistics: ', 'FAIL'])
#                         self.logger.info('Test Verify TCP proxy statistics is FAILED')
#                         flag = flag + 1
