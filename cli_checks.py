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
import random
import time
import operator
import pprint
import ipaddress
from ipaddress import IPv4Network
from ipaddress import IPv4Address
from collections import OrderedDict
from collections import defaultdict
from time import sleep
from math import pi
from profile import *
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
sys.path.insert(0, os.path.join(main_dir, 'vmanage'))
sys.path.insert(0, os.path.join(main_dir, 'suites'))
# from lib.gvmanage_session.configuration.Templates import Templates
# from lib.gvmanage_session import Basics
# from lib.vmanage_session.VManageSession import VManageSession
# from vmanage.scripts.vmanage_session import VmanageSession

args_obj = Args()
run = Runner(os.path.basename(__file__)[:-3], args_obj)

class cli_checks(object):
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

    @run.test(['Appqoe_events'])
    def Appqoe_events(self):
        pm_vedges = ['pm9009']
        appqoe_status= self.test_appqoe_hardware_qfp_active_stats()
        appqoe_qft_status = self.nat_statistics()
        appqoe_rm_resuorce_status = self.tcp_proxy_statistics()
        appqoe_tcp_connection_status = self.test_appqoe_libuinet_stats()
        appqoe_rm_stats = self.test_appqoe_rm_stats()


    def tcp_proxy_statistics(self, device='pm9009'):
        cmd = 'show tcpproxy statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        result = {}
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        return result


    def nat_statistics(self, device='pm9009'):
        cmd = 'show sdwan appqoe nat-statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        # print output
        result = {}
        for line in output.split('\n'):
            self.key_value_dict(line, result)
        return result


    def key_value_dict(self, line, dictionary):
        match = re.match(r'.*:.*', line)
        if match:
            line = line.split(':')
            key = line[0].strip()
            value = line[1].strip()
            dictionary[key]=value
        return dictionary


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



    def hubSpokeCheck(self,hostname):
        match = 0
        pm_vedges=self.topology.pm_vedge_list()
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
            for line in output.split('\n'):
                if system_ip in line:
                    foundCount = 0
            if  foundCount == 0:
                match = 0
            else:
                match = match + 1
        if match == 0 :
            return[True,'Hub and Spoke check is Passed']
        else:
            return[False,'Hub and Spoke check is Failed']


    def get_match(self, regex_dict, line):
        """
        matches a given line against all the compiled regex
        in the regex dictionary ('regex_name', compiled_obj)
        returns the matched object or None.
        """
        rx = None
        match_obj = None
        for regex in regex_dict.keys():
            compiled_obj = regex_dict[regex]

            match_obj = compiled_obj.match(line)

            if match_obj:
                rx = regex
                break
        return rx, match_obj


    def qos_stats(self, device, interface):
        cmd = 'show policy-map interface '+str(interface)
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
        return resultdict1


    def test_appqoe_hardware_qfp_active_stats(self, device='pm9009'):
        cmd = 'show platform hardware qfp active feature appqoe stats all'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        # print output
        parsed_output = output.split('\n')
        # parsed_output = [string.strip() for string in parsed_output if (string != "" and re.match(r'.*:.*', string))]
        parsed_output = [string.strip() for string in parsed_output if (string != "")]
        global_stats_index = parsed_output.index('Global:')
        sdvt_global_stats_index = parsed_output.index('SDVT Global stats:')
        sn_green_stats_index = parsed_output.index('SN Index [0 (Green)]')
        sn_default_stats_index = parsed_output.index('SN Index [Default]')
        global_stats = {}
        sdvt_global_stats = {}
        sn_green_stats = {}
        sn_default_stats = {}
        for line in parsed_output[global_stats_index+1:sdvt_global_stats_index]:
            self.key_value_dict(line, global_stats)
        for line in parsed_output[sdvt_global_stats_index+1:sn_green_stats_index]:
            self.key_value_dict(line, sdvt_global_stats)
        for line in parsed_output[sn_green_stats_index+1:sn_default_stats_index]:
            self.key_value_dict(line, sn_green_stats)
        for line in parsed_output[sn_default_stats_index+1:]:
            self.key_value_dict(line, sn_default_stats)
        test_appqoe_qfp_active_stats = global_stats, sdvt_global_stats, sn_green_stats, sn_default_stats
        return test_appqoe_qfp_active_stats

    def test_appqoe_libuinet_stats(self, device='pm9009'):
        cmd = 'show sdwan appqoe libuinet-statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
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
            self.key_value_dict(line, sppi_stats)
        for line in parsed_output[vpath_stats_index+1:]:
            self.key_value_dict(line, vpath_stats)
        appqoe_libuinet_stats = sppi_stats, vpath_stats
        # print appqoe_libuinet_stats
        return appqoe_libuinet_stats

    def test_appqoe_rm_stats(self, device='pm9009'):
        cmd = 'show sdwan appqoe rm-statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        self.logger.info(output)
        parsed_output = output.split('\n')
        parsed_output = [string.strip() for string in parsed_output if (string != "" and re.match(r'.*:.*', string))]
        client_tcp_index = parsed_output.index('Client: TCP')
        client_ssl_index = parsed_output.index('Client: SSL')
        client_dre_index = parsed_output.index('Client: DRE')
        client_http_index = parsed_output.index('Client: HTTP')
        client_ad_index = parsed_output.index('Client: AD')
        time_sessions = {}
        client_tcp_stats = {}
        client_ssl_stats = {}
        client_dre_stats = {}
        client_http_stats = {}
        client_ad_stats = {}
        for line in parsed_output[:client_tcp_index]:
            self.key_value_dict(line, time_sessions)
        for line in parsed_output[client_tcp_index+1:client_ssl_index]:
            self.key_value_dict(line, client_tcp_stats)
        for line in parsed_output[client_ssl_index+1:client_dre_index]:
            self.key_value_dict(line, client_ssl_stats)
        for line in parsed_output[client_dre_index+1:client_http_index]:
            self.key_value_dict(line, client_dre_stats)
        for line in parsed_output[client_http_index+1:client_ad_index]:
            self.key_value_dict(line, client_http_stats)
        for line in parsed_output[client_ad_index+1:]:
            self.key_value_dict(line, client_ad_stats)
        appqoe_rm_stats = time_sessions, client_tcp_stats, client_ssl_stats, client_dre_stats, client_http_stats, client_ad_stats
        self.logger.info(appqoe_rm_stats)
        return appqoe_rm_stats


    def check_zbfw_global_statistics_cedge(self, device):
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        cmd1 = 'show  sdwan zbfw zonepair-statistics | incl pkt-counters'
        cmd2 = 'show sdwan zbfw drop-statistics'
        pkt_counters = self.confd_client.sendline(dest_ip, cmd1)
        drop_statistics = self.confd_client.sendline(dest_ip, cmd2)
        try:
            pkt_counters = pkt_counters["message"]
            drop_statistics_str = drop_statistics["message"]
            pkt_counters = pkt_counters.split("\n")[1:-1]
            pkt_counters = [int(counter.split(" ")[-1]) for counter in pkt_counters]
            drop_statistics = drop_statistics_str.split("\n")[1:-2]
            drop_statistics_dict = {}
            drop_sum = 0
            for stat in drop_statistics:
                stat_list = stat.split()
                drop_statistics_dict[stat_list[1]] = int(stat_list[-1])
                drop_sum += int(stat_list[-1])
            pkt_sum = 0
            for counter in pkt_counters:
                pkt_sum += counter
            if pkt_sum ==0:
                return [False, "You didn't record any zbfw packets"]
            if drop_sum/(pkt_sum + 1) > .001:
                return [False, "You had more than .001% failures"]
            else:
                return [True, "ZBFW counters look good. %d packets %d drops"%(pkt_sum, drop_sum)]
        except:
            self.logger.info("you recieved an error or pexpect OBO when gathering zbfw stats")
            return [False, "you recieved an error or pexpect OBO when gathering zbfw stats"]
        return [True, "You didn't have any concerning zbfw global-statistics"]


    def check_zbfw_global_statistics_vedge(self, device):
        dest_ip = self.topology.mgmt_ipaddr(device)
        cmd = 'show policy zbfw global-statistics'
        stats = self.confd_client.parse_counter_table(dest_ip, cmd='show policy zbfw global-statistics')
        if not "Total zone-based firewall packets" in stats.keys():
            return [False, "no ZBFW packets logged"]
        total_packets = int(stats["Total zone-based firewall packets"]) + 1 #adding 1 to avoid division by 0
        fail_bool = False
        fail_bool = fail_bool or (stats["State check failures"]/total_packets > FAIL_THRESH)
        fail_bool = fail_bool or (stats["Fragment failures"]/total_packets > FAIL_THRESH)
        fail_bool = fail_bool or (stats["Fragments"]/total_packets > FAIL_THRESH)
        fail_bool = fail_bool or (stats["Flow addition failures"] > 0)
        fail_bool = fail_bool or (stats["Unsupported protocol"] > 0)
        fail_bool = fail_bool or (stats["Exceeded maximum TCP half-open"] > 0)
        fail_bool = fail_bool or (stats["Mailbox message full"] > 0)
        if fail_bool:
            # self.logger.info(self.confd_client.sendline(src_ip, "show policy zbfw global-statistics")['message'])
            return [False, "You had more than .001% failures or another failure counter was non-zero after well-formed ixia traffic"]
        else:
            return [True, "You didn't have any concerning zbfw global-statistics"]


    def clear_zbfw_statistics(self,device):
        dest_ip = self.topology.mgmt_ipaddr(device)
        if self.topology.is_cedge(dest_ip):
            res = self.confd_client.sendline(dest_ip, "show platform hardware qfp active feature firewall drop clear")
            res = self.confd_client.sendline(dest_ip, "clear zone-pair counter")
        else:
            res = self.confd_client.sendline(dest_ip, "clear policy zbfw global-statistics")
            stats = stats = self.confd_client.parse_counter_table(dest_ip, cmd='show policy zbfw global-statistics')
            for key in stats.keys():
                if int(stats[key]) > 0:
                    # self.logger.info(self.confd_client.sendline(src_ip, "show policy zbfw global-statistics")['message'])
                    return [False, "after clearing zbfw global statistics, there were still non-zero entries"]
        return [True, "zbfw global-statistics were fully cleared"]


    def check_zbfw_global_statistics(self, device):
        dest_ip = self.topology.mgmt_ipaddr(device)
        if self.topology.is_cedge(dest_ip):
            return self.check_zbfw_global_statistics_cedge(device)
        else:
            return self.check_zbfw_global_statistics_vedge(device)


    def check_zbfw_sessions(self, device='pm9009'):
        dest_ip = self.topology.mgmt_ipaddr(device)
        if self.topology.is_cedge(dest_ip):
            sessions = self.confd_client.sendline(dest_ip, "show sdwan zonebfwdp sessions")
        else:
            sessions = self.confd_client.sendline(dest_ip, "show policy zbfw sessions")
        sessions = sessions["message"]
    	if "No entries found" in sessions:
    	    return [True, "no zbfw sessions found"]
    	return[False , "zbfw sessions found when no inspect action is configured"]

    def test_clear_SSLProxy_Statistics(self,device):
        cmd = 'clear sslproxy statistics'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        return [True, 'SSLproxy statistics are cleared']

    @run.test(['verify_fnf'])
    def fnf_drop(self,device='pm9009'):
        cmd="show sdwan app-fwd cflowd flows format table"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0", timeout=300)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        import pdb; pdb.set_trace()
        if len(output) == 0:
            print("Empty value passed as part of show output")
            return [False, []]
        else:
            temp = output.split("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
            if len(temp[1]) == 0:
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


    def fnf_egress(device, srcip = '', dstip = '', exp_op = ''):
        cmd="show sdwan app-fwd cflowd flows format table"
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        if len(output) == 0 | len(srcip) == 0 | len(dstip) == 0:
            print("Empty value passed in show output or in srcip or in dstip")
            return [False, []]
        else:
            temp = output.split("---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")
            if len(temp[1]) == 0:
                print("No flow values available as part of show output")
                return [False, []]
            else:
                egress_list = []
                val = temp[1].strip()
                flow_values = val.split("\n")
                for i in range(len(flow_values)):
                    get = flow_values[i].split()
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

	def dump_on_fail(self,vip_box='192.168.1.38'):
		no_timeout = self.confd_client.sendline(vip_box, "terminal length 0")
		cmds = ['show platform software nat fp active interface',
				'show platform hardware qfp active feature nat datapath drop',
				'show ip nat translations']
		for i in cmds:
			cmd_out = self.confd_client.sendline(vip_box,i)
			cmd_out = cmd_out["message"]
			print(cmd_out)
			print("\n")

    @run.test(['verify_provisioning'])
    def verify_provisioning(self,vip_box='192.168.1.38'):
        print("Verify the provisioning first")
        import pdb; pdb.set_trace()
        err_flag = 0
        nat_route = self.confd_client.sendline(vip_box, 'sh ip route vrf 1 | inc n*Nd')
        nat_route = nat_route["message"]
        line2 = re.split('\n',nat_route)
        line2.pop(0)
        line2.pop(-1)
        found = 0
        for i in line2:
            if re.match('^n\*Nd(.*)',i):
                found = 1
                break
            else:
                found=0
        if(found == 1):
            print("Default NAT route FOUND")
        else:
            print("DEfault route NOT found")
            err_flag = 1

        nat_config = self.confd_client.sendline(vip_box, 'show run | inc ip nat')
        nat_config = nat_config["message"]
        line2 = re.split('\n',nat_config)
        line2.pop(0)
        line2.pop(-1)

        if(nat_config == ' '):
            print("No output Found")

        line2 = re.split('\n',nat_config)

        for i in line2:
            if(re.match('^ip nat inside source list ([a-zA-Z\-]+)\sinterface\s([a-zA-Z0-9\/]+)\soverload',i)):
                print("interface overload found")
                out = re.match('^ip nat inside source list ([a-zA-Z\-]+)\sinterface\s([a-zA-Z0-9\/]+)\soverload',i)
                print("overload interface is %s" %out.group(2))
                found = 1

        if(found == 0):
            print("No configs for interface/pool")
            err_flag = 1

        if(err_flag == 1):
            print("Provisioning Failed")
            self.dump_on_fail(vip_box)
            return [False, 'Provisioning Failed']
        else:
            print("Provisioning passed, Proceed with CLI Checks")
            return [True, "Provisioning passsed"]

    def get_nat_sess(self,sess_out):
        line = re.split('\n',sess_out)
        line.pop(0)
        line.pop(-1)
        line.pop(-1)
        sess = {}
        j=-1
        for i in line:
            i.strip()
            if(re.match("^nat-fwd ip-nat-translation",i)):
                j = j + 1
                sess[j] = {}
                (ig1,ig2,s_add,d_add,s_port,d_port,na,prot,ig3) = re.split('\s',i)
                sess[j]['src_addr'] = s_add
                sess[j]['dst_addr'] = d_add
                sess[j]['src_port'] = s_port
                sess[j]['dst_port'] = d_port
                sess[j]['prot'] = prot
            else:
                if(i == ''):
                    break
                a = re.match('^([a-zA-Z \-]+)\s+([0-9\.]+)',i)
                key = a.group(1)
                key = key.strip()
                sess[j][key] = a.group(2)
		pprint.pprint(sess)
        return sess

    @run.test(['verify_nat_stats'])
    def verify_nat_stats(self,vip_box='192.168.1.38'):
        no_timeout = self.confd_client.sendline(vip_box, "terminal length 0")
        nat_stat = self.confd_client.sendline(vip_box, 'show ip nat statistics')
        stats_dict = {'total_act' : 20, 'dynamic': 20, 'in_to_out_drops': 0}
        nat_stat = nat_stat["message"]
        if(nat_stat == ' '):
            return [False, 'No output for show ip nat statistics']
        line1 = re.split('\n',nat_stat)
        line1.pop(0)
        line1.pop(-1)
        nat_out = {}
        error = 0
        for i in line1:
            if re.match('^Total active translations:\s(\d+)\s\W(\d+)\sstatic, (\d+) dynamic; (\d+)(.*)',i):
                out = re.match('^Total active translations:\s(\d+)\s\W(\d+)\sstatic, (\d+) dynamic; (\d+)(.*)',i)
                nat_out['total_act'] = out.group(1)
                nat_out['static'] = out.group(2)
                nat_out['dynamic'] = out.group(3)
                nat_out['extended'] = out.group(4)
            elif re.match('^Hits.*',i):
                out = re.match('^Hits: (\d+)\s+Misses: (\d+)',i)
                nat_out['hits'] = out.group(1)
                nat_out['misses'] = out.group(2)
            elif re.match('(^[a-zA-Z \-]+): (\d+)$',i):
                out = re.match('(^[a-zA-Z \-]+): (\d+)$',i)
                key = out.group(1)
                key = re.sub('\s+|\-', '_',key)
                key = key.lower()
                nat_out[key] = out.group(2)
            elif re.match('(^[a-zA-Z \-]+): (\d+)\s+([a-zA-Z \-]+): (\d+)',i):
                out = re.match('(^[a-zA-Z \-]+): (\d+)\s+([a-zA-Z \-]+): (\d+)',i)
                key1 = out.group(1)
                key2 = out.group(3)
                key1 = re.sub('\s+|\-', '_',key1)
                key1 = key1.lower()
                key2 = re.sub('\s+|\-', '_', key2)
                key2 = key2.lower()
                nat_out[key1] = out.group(2)
                nat_out[key2] = out.group(4)
            elif re.match('^\s+max entry',i):
                out = re.match('^\smax entry: max allowed (\d+), used (\d+), missed (\d+)',i)
                nat_out['max_entry_allowed'] = out.group(1)
                nat_out['max_entry_used'] = out.group(2)
                nat_out['max_entry_missed'] = out.group(3)
        pprint.pprint(nat_out)

        for key in stats_dict:
            if(int(nat_out[key]) >= int(stats_dict[key])):
                print("values matched for key %s" %key)
            else:
                error = 1
                print("Values not matched for key %s" %key)
                print("output for key %s Actual %s, Passed %s"%(key,nat_out[key],stats_dict[key]))

        if(error == 1):
            return [False, 'Some verificcation falied']
        else:
            return [True, 'All verifications passed']

    @run.test(['verify_nat_sess'])
    def verify_nat_sess(self,vip_box='192.168.1.38',target_dict=''):
        sess_out = self.confd_client.sendline(vip_box, 'show sdwan nat-fwd ip-nat-translation')
        sess_out = sess_out["message"]
        sess = self.get_nat_sess(sess_out)
        target_dict = { 'src_addr': '173.19.51.0/24',
        	'dst_addr': '99.99.99.0/24',
        	'inside-global-addr' : '30.30.30.2',
        	'inside-global-port' : '1024-65535',
        	'application-type' : '0'
        	}

        j = 0
        error = 0
        for j in range(len(sess)):
            # print "verifying sess", j, sess
            for val in target_dict:
                if (val == "src_addr" or val == "dst_addr" or val == "inside-global-addr"):
                    target = target_dict[val]
                    actual = sess[j][val]
                    if re.findall('/',target):
                        print("match the range")
                        if (IPv4Address(unicode(actual)) in IPv4Network(unicode(target))):
                            print("matched")
                        else:
                            print("%s IP not within the range %s" %(actual,target))
                            error = 1
                    else:
                        if(IPv4Address(unicode(actual)) == IPv4Address(unicode(target))):
                            print("Matcch the 2 ip addresses")
                        else:
                            print("IP's did not match")
                            error = 1
                elif (val == "inside-global-port"):
                    target_port = target_dict[val]
                    actual_port = sess[j][val]
                    (low,high) = re.split('-',target_port)
                    if(actual_port >= low and actual_port <= high):
                        print("Ports within the range")
                    else:
                        print("Ports did not match")
                        error = 1
                else:
                    if(target_dict[val] == sess[j][val]):
                        print("%s field matched" %val)
                    else:
                        print("%s Fields did not match" %val)
                        error = 1
            j = j+1
            if(j >= len(sess)):
                break
        if(error == 1):
            print("Failed")
            #return True
            return[False, "Verification falied"]
        else:
            print("Passed")
            return[True, 'Verification Passed']

    def show_vrf_details(self,device='pm9009'):
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

    @run.test(['verify_flows'])
    def verify_sdwan_appqoe_flows(self,device='pm9009', vrfvalue='1', server_port='80'):
        cmd = 'show sdwan appqoe flow vpn-id {} server-port {}'.format(vrfvalue, server_port)
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        for line in output.split('\n'):
            if 'No Matching Flows' in line:
                return [False,'No matching flows found']
            regex = re.search(r'[0-9]+\s([0-9]+)\s+([0-9.]+)[:0-9]+\s+([0-9.:]+)', line)
            if regex:
                if regex.group(1) == vrfvalue:
                    self.logger.info('flows matched')
                else:
                    flag = flag + 1
        if flag == 0:
            return [True,'Matching Flows found']
        else:
            return [False,'No Matching Flows found']

    def show_tunnel_statistics_pkt_dup(self, device):
        cmd = 'show sdwan tunnel statistics pkt-dup'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        parsed_output = output.split('\n')
        parsed_output = [string.strip() for string in parsed_output if (string != "" and "tunnel" not in string)]
        pktdup_rxpattern = re.compile(r'^pktdup-rx$')
        pktdup_rx_other_pattern = re.compile(r'^pktdup-rx-other$')
        pktdup_rx_this_pattern = re.compile(r'^pktdup-rx-this$')
        pktdup_tx_pattern = re.compile(r'^pktdup-tx$')
        pktdup_tx_other_pattern = re.compile(r'^pktdup-tx-other$')
        pktdup_capable = re.compile(r'^pktdup-capable$')
        d = defaultdict(list)
        for line in parsed_output:
            line = line.split()
            if re.match(pktdup_rxpattern, line[0]):
                d['pktdup-rx'].append(line[1])
            if re.match(pktdup_rx_other_pattern, line[0]):
                d['pktdup-rx-other'].append(line[1])
            if re.match(pktdup_rx_this_pattern, line[0]):
                d['pktdup-rx-this'].append(line[1])
            if re.match(pktdup_tx_pattern, line[0]):
                d['pktdup-tx'].append(line[1])
            if re.match(pktdup_tx_other_pattern, line[0]):
                d['pktdup-tx-other'].append(line[1])
            if re.match(pktdup_capable, line[0]):
                d['pktdup-capable'].append(line[1])
        return d

    def show_tunnel_statistics_fec(self, device):
        cmd = 'show sdwan tunnel statistics fec'
        dest_ip = self.topology.mgmt_ipaddr(device)
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']
        parsed_output = output.split('\n')
        parsed_output = [string.strip() for string in parsed_output if (string != "" and "tunnel" not in string)]
        fec_rx_data_packets = re.compile(r'^fec-rx-data-pkts$')
        fec_rx_parity_pkts = re.compile(r'^fec-rx-parity-pkts$')
        fec_tx_data_pkts= re.compile(r'^fec-tx-data-pkts$')
        fec_tx_parity_pkts = re.compile(r'^fec-tx-parity-pkts$')
        fec_reconstruct_pkts = re.compile(r'^fec-reconstruct-pkts$')
        fec_capable = re.compile(r'^fec-capable$')
        fec_dynamic = re.compile(r'^fec-dynamic$')
        d = defaultdict(list)
        parsed_output = filter(None, parsed_output)
        for line in parsed_output:
            line = line.split()
            if re.match(fec_rx_data_packets, line[0]):
                d['fec-rx-data-pkts'].append(line[1])
            if re.match(fec_rx_parity_pkts, line[0]):
                d['fec-rx-parity-pkts'].append(line[1])
            if re.match(fec_tx_data_pkts, line[0]):
                d['fec-tx-data-pkts'].append(line[1])
            if re.match(fec_tx_parity_pkts, line[0]):
                d['fec-tx-parity-pkts'].append(line[1])
            if re.match(fec_reconstruct_pkts, line[0]):
                d['fec-reconstruct-pkts'].append(line[1])
            if re.match(fec_capable, line[0]):
                d['fec-capable'].append(line[1])
            if re.match(fec_dynamic, line[0]):
                d['fec-dynamic'].append(line[1])

    @run.test(['test_sample'])
    def show_bfd(self,device='pm9009'):
        import pdb; pdb.set_trace()
        cmd = 'show sdwan bfd summary'
        dest_ip = self.topology.mgmt_ipaddr(device)
        no_timeout = self.confd_client.sendline(dest_ip, "terminal length 0")
        output = self.confd_client.sendline(dest_ip, cmd)
        output = output['message']

    def get_config(self,res):
        data = res.content
        data = json.loads(data)
        data = data['config']
        return data

if __name__ == '__main__':
    import pdb; pdb.set_trace()
    run.call_all(cli_checks)
