__author__ = 'diansan'

from ..Basics import Basics
import os
import sys
import json
main_dir = os.path.dirname(sys.path[0])
sys.path.insert(0, main_dir)
sys.path.insert(0, os.path.join(main_dir, 'lib'))
from lib.gvmanage_session import Basics

class Dashboard(Basics):
    def __init__(self, data, logger):
        super(Dashboard, self).__init__(data, logger)

    # functions shared by provider and tenant
    def _get_reachable_device_status(self, profile, expectation, device_personality):
        mount_point = '/device/reachable'
        url = self._generate_url(profile.vmanage_hostname, mount_point, personality = device_personality)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def _get_unreachable_device_status(self, profile, expectation, device_personality):
        mount_point = '/device/unreachable'
        url = self._generate_url(profile.vmanage_hostname, mount_point, personality = device_personality)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)


    ####################################################################################################################
    # <str> device_personality can be selected from :
    #   'vbond', 'vsmart', 'vedge'
    ####################################################################################################################
    def get_reachable_device_status(self, profile, expectation, device_personality):
        return self._get_reachable_device_status(profile, expectation, device_personality)

    ####################################################################################################################
    # <str> device_personality can be selected from :
    #   'vbond', 'vsmart', 'vedge'
    ####################################################################################################################
    def get_unreachable_device_status(self, profile, expectation, device_personality):
        return self._get_unreachable_device_status(profile, expectation, device_personality)

    def verify_dashboard_vedge_widget_control_with_csp(self, profile, device_list):
        """Verify control connection of device with vManage. """
        dev_list = []
        for device in device_list:
            dev_list.append({'uuid':device})
        expectation = {'status_code': 200,'present': {'data' : dev_list}}
        device_personality = 'vedge'
        return self.get_reachable_device_status(profile, expectation, device_personality)

    def get_connection_summary(self, profile, expectation):
        mount_point = '/network/connectionssummary'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    #  For tenant's table
    def get_all_tenant_status(self, provider_profile, expectation):
        mount_point = '/tenantstatus'
        url = self._generate_url(provider_profile.vmanage_hostname, mount_point)
        headers = {'Host': provider_profile.domain_name}
        return self.http_request(provider_profile, 'GET', url, headers, None, expectation = expectation)

    def get_vmanage_status_summary(self, provider_profile, expectation):
        mount_point = '/clusterManagement/health/summary'
        url = self._generate_url(provider_profile.vmanage_hostname, mount_point)
        headers = {'Host': provider_profile.domain_name}
        return self.http_request(provider_profile, 'GET', url, headers, None, expectation = expectation)

    def get_vmanage_status_details(self, provider_profile, expectation):
        mount_point = '/clusterManagement/health/details'
        url = self._generate_url(provider_profile.vmanage_hostname, mount_point)
        headers = {'Host': provider_profile.domain_name}
        return self.http_request(provider_profile, 'GET', url, headers, None, expectation = expectation)

    def get_cert_state_summary(self, provider_profile, expectation):
        mount_point = '/certificate/stats/summary'
        url = self._generate_url(provider_profile.vmanage_hostname, mount_point)
        headers = {'Host': provider_profile.domain_name}
        return self.http_request(provider_profile, 'GET', url ,headers, None, expectation = expectation)

    def get_cert_state_details(self, provider_profile, expectation):
        mount_point = '/certificate/stats/detail'
        url = self._generate_url(provider_profile.vmanage_hostname, mount_point)
        headers = {'Host': provider_profile.domain_name}
        return self.http_request(provider_profile, 'GET', url ,headers, None, expectation = expectation)

    # tenant's dashboard
    # For Control Status
    def get_control_status_summary(self, tenant_profile, expectation):
        mount_point = '/device/control/count'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    ####################################################################################################################
    # <str> state can be selected from: 'up', 'partial', 'down'
    ####################################################################################################################
    def get_control_status_details(self, tenant_profile, expectation, state):
        mount_point = '/device/control/networksummary?state=%s' % state

    # For Site Health View
    def get_bfd_sites_summary(self, tenant_profile, expectation):
        mount_point = '/device/bfd/sites/summary'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    ####################################################################################################################
    # <str> state can be selected from: 'siteup', 'sitepartial', 'sitedown'
    ####################################################################################################################
    def get_bfd_sites_details(self, tenant_profile, expectation, state):
        mount_point = '/device/bfd/sites/detail?state=%s' % state
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    # For Transport Interface Distribution
    def get_tloc_util_summary(self, tenant_profile, expectation):
        mount_point = '/device/tlocutil'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    ####################################################################################################################
    # <str> state can be selected from: 'lessthan10mbps', '', '', ''
    ####################################################################################################################
    def get_tlocl_util_details(self, tenant_profile, expectation, util):
        mount_point = '/device/bfd/sites/detail?state=%s' % util
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    # For vEdge Inventory
    def get_vedge_inventroy_summary(self, tenant_profile, expectation):
        mount_point = '/device/vedgeinventory/summary'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    # For Edge Health
    def get_vedge_health_summary(self, tenant_profile, expectation):
        mount_point = '/device/hardwarehealth/summary?isCached=true'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    # For Reboot
    def get_reboot_count(self, tenant_profile, expectation):
        mount_point = '/network/issues/rebootcount'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    def get_reboot_history_details(self, tenant_profile, expectation):
        mount_point = '/device/reboothistory/details'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    # unknown
    def get_crash_log_details(self, tenant_profile, expectation):
        mount_point = '/device/crashlog/details'
        url = self._generate_url(tenant_profile.vmanage_hostname, mount_point)
        headers = {'Host': tenant_profile.domain_name}
        return self.http_request(tenant_profile, 'GET', url, headers, None, expectation = expectation)

    def get_device_activity_status(self, profile, expectation, response_code):
        mount_point = '/device/action/status/{}'.format(response_code)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_alarm_count(self, profile, expectation):
        mount_point = '/alarms/count'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_tenant_control_status(self, profile, expectation):
        mount_point = '/device/control/count?isCached=true'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_tenant_site_health_view(self, profile, expectation):
        mount_point = '/device/bfd/sites/summary?isCached=true'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def device_crashlog(self, profile, expectation,deviceId):
        self.updateToken(profile)
        mount_point = "/device/crashlog/"\
                '?deviceId={id}'.format(id=deviceId)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_device_Hardware_errors(self, profile, expectation):
        self.updateToken(profile)
        mount_point = 'device/hardware/errors'
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_hardware_status_summary(self, profile, expectation):
        self.updateToken(profile)
        mount_point = '/device/hardware/status/summary'\
                    '?deviceId={id}'.format(id=deviceId)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)

    def get_hardware_system_datalist(self, profile, expectation, deviceId):
        self.updateToken(profile)
        mount_point = '/device/hardware/system'\
                    '?deviceId={id}'.format(id=deviceId)
        url = self._generate_url(profile.vmanage_hostname, mount_point)
        headers = {'Host': profile.domain_name}
        return self.http_request(profile, 'GET', url, headers, None, expectation = expectation)
