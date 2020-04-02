Steps to Execute Reboot script.
1. source the profile.
   source ~/.profile
2. Execute "run.py" which is located under  "/home/tester/vtest-tools/confd_server"
   python run.py
3. Execute the below commands in Jumphost
   unset http_proxy
   unset https_proxy
4. Install texttable package in your Jumphost.
   python2.7 -m pip install texttable
5. Go to "/home/tester/vtest-tools/" path in your jumhost and copy the entire "lib" folder from 10.104.45.88
   cd /home/tester/vtest-tools/
   scp -r tester@10.104.45.88:/home/tester/vtest-tools/lib/ .
6. Go to "/home/tester/vtest-tools/flat_input/topology_yamls/" and copy the "bglsystemtestbed.yaml" file from 10.104.45.88.
   Note: you might have a yaml file in your jumphost for CLI regression with the same name "bglsystemtestbed.yaml"
   If you already have a yaml file with that same name""bglsystemtestbed.yaml"" then rename it. As of now copy and use "bglsystemtestbed.yaml" for REST API 
   cd /home/tester/vtest-tools/flat_input/topology_yamls/
   scp tester@10.104.45.88:/home/tester/vtest-tools/flat_input/topology_yamls/bglsystemtestbed.yaml .
7. Go to "/home/tester/vtest-tools/suites" path and copy "BglSystemtestbedDeviceConfigs" folder from 10.104.45.88
   cd /home/tester/vtest-tools/suites/
   scp -r tester@10.104.45.88:/home/tester/vtest-tools/suites/BglSystemtestbedDeviceConfigs/ .
8. Copy vivek_appqoe_system.py file from 10.104.45.88.
   cd /home/tester/vtest-tools/suites/
   scp tester@10.104.45.88:/home/tester/vtest-tools/suites/vivek_appqoe_system.py.
9. You need make below changes in the code. Currently these steps are static we will be modifying these codes soon.
   open vivek_appqoe_system.py and search and modify the device names according to your setup.

   DEVICE_TYPE['pm9006']   = 'vedge-ASR-1002-HX'
   DEVICE_TYPE['pm9008']   = 'vedge-ASR-1002-HX'
   DEVICE_TYPE['pm9007']   = 'vedge-1000'
   DEVICE_TYPE['pm9011']   = 'vedge-2000'
   DEVICE_TYPE['pm9009']   = 'vedge-ISR-4351'
   DEVICE_TYPE['pm9010']   = 'vedge-ISR-4461'
   DEVICE_TYPE['pm9012']   = 'vedge-2000'

10. Provide the list of boxes in pm_vedges list for reboot.
    Number of devices and reboots can be changed in the below code according to your setup and requirement.
    @run.test(['RebootDevices'])
    def RebootDevices(self):
       pm_vedges = ['pm9006'] # change the list according to the setup:ex: ['pm9006', 'pm9008']
       pm_vedges = ['pm9006']
       failcount = 0
       PushfailedDevices = []
       table_result = []
       for i in range(1): # Number of reboot need to mentioned inside range. ex:range(50)
    
       
11. You need to create the template before executing the script.
