'''
This automation is intended to show/demo 802.1Qbv

Topology
                          DUT
Ixia Port 1 ----------- NXP spw0
Ixia Port 2 ----------- NXP spw1 ( Egress )

Cycle Time = 1,000 microseconds
4 Windows
Window 1 -   0 to  250 Microseconds - Vlan Priorities 0,1,2,3  = 0 0 0 0  1 1 1 1  = 0x0F
Window 2 - 250 to  500 Microseconds - Vlan Priorities 4        = 0 0 0 1  0 0 0 0  = 0x10
Window 1 - 500 to  750 Microseconds - Vlan Priorities 5        = 0 0 1 0  0 0 0 0  = 0x20
Window 1 - 750 to 1000 Microseconds - Vlan Priorities 6,7      = 1 1 0 0  0 0 0 0  = 0xC0

+++++ END OF DUT CONFIG +++++++++++++++++++



'''

import sys
from ixnetwork_restpy import *
import locale

locale.setlocale(locale.LC_ALL, '')
import time
from helperFunctions import *
import math
from datetime import datetime, timedelta
from decimal import Decimal, getcontext
import traceback

TestVars = testVars()
TestVars.chassisIp : str = '10.80.81.77'
TestVars.sessionIp : str = 'localhost'
TestVars.UrlPrefix = None
TestVars.dut_ip : str = '10.80.81.6' 
TestVars.dut_username : str = 'root' 
TestVars.dut_password : str = ""


# Session ID for now is None; meaning we are creating a new session.
TestVars.sessionId : str = 1
TestVars.port1 : str = '1/1'
TestVars.port2 : str = '1/2'
TestVars.cleanConfig : bool = True
TestVars.takePorts : bool = True
TestVars.user : str =  'admin'
TestVars.password : str = 'Keysight#12345'
TestVars.UrlPrefix=None

# Pkt Sizes to test 'min:max:incrBy'
TestVars.pktSize_in_bytes: int = 100
#TestVars.txClycleTime_in_microseconds : str = '1000'
TestVars.Preamble_in_bytes : int = 8
TestVars.InterFrameGap_in_bytes : int = 12
TestVars.vlan_id : int = 100

# Expecting Lists of Lists....to calculate number of queues
#TestVars.vlan_priorities : list = [[0],[4],[5],[7]]
#TestVars.cycle_time_in_microseconds : list = [250,250,250,250]

TestVars.gates : list = [
    {'vlan_pri' : [0,1,2,3] , 'gate_open_microseconds' : 250, 'gate_state' : 'OCCCCCCC'},
    {'vlan_pri': [4], 'gate_open_microseconds': 250, 'gate_state' : 'COCCCCCC'},
    {'vlan_pri': [5], 'gate_open_microseconds': 250, 'gate_state' : 'CCOCCCCC'},
    {'vlan_pri': [6,7], 'gate_open_microseconds': 250, 'gate_state' : 'CCCOCCCC'},
]

TestVars.preamble_in_bytes : int = 8
TestVars.inter_frame_gap_in_bytes : int = 12
TestVars.data_rate_in_Gbps : int = 1
TestVars.gPtp_profile : str = 'ieee8021asrev'
TestVars.session_name = 'cc'
TestVars.rest_port = 11009

# Mini Automation 
TestVars.mini_flag : bool = False
if TestVars.mini_flag:
    TestVars.rest_port = 80  
    TestVars.sessionId = None
    TestVars.UrlPrefix="ixnetwork-mw"
    TestVars.user  =  None
    TestVars.session_name = None
    TestVars.chassisIp : str = 'localchassis'


def main():

    # description
    outLogFile : str = 'validadeQvb_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
    if TestVars.session_name: 
        TestVars.session_name : str = 'validadeQvb_' + "me" + time.strftime("%Y%m%d-%H%M")
    vport_dic = dict()
    myStep = Step()

    macs = MacAddressGenerator()

    try:
        session = SessionAssistant(IpAddress=TestVars.sessionIp,
                                   UserName=TestVars.user,
                                   Password=TestVars.password,
                                   RestPort=TestVars.rest_port,
                                   SessionId=TestVars.sessionId,
                                   SessionName=TestVars.session_name,
                                   ClearConfig=TestVars.cleanConfig,
                                   LogLevel='info',
                                   UrlPrefix=TestVars.UrlPrefix,
                                   LogFilename=outLogFile)

    except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform at {TestVars.chassisIp}")
        print(f"Details: {conn_err}")
    except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
    except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform: {my_vars['Global']['rest_session']}")
        print(f"Details: {not_found_err}")
    except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
    except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")
        print(traceback.format_exc())

    ixnet_session = session.Ixnetwork

    # Prepare DUT 
    try:
        # Reboot the server and reconnect
        client = reboot_and_wait(TestVars.dut_ip, TestVars.dut_username, TestVars.dut_password)
        # After reconnecting, run the fgptp.sh start script
        print("Running avb.sh start ...")
        stdin, stdout, stderr = client.exec_command("fgptp.sh start")  # Replace with the correct path if needed

        time.sleep(30)
        print("Running Qbv setup...")
        #stdin, stdout, stderr = client.exec_command("./qbv/set_qbv_1ms_4q.sh")

        time.sleep(10)

        print("Adding egress traffic static L2 route ...")
        stdin, stdout, stderr = client.exec_command("bridge fdb add 00:01:ca:ff:ee:99 dev swp1 master static")

        time.sleep(10)

        # Ensure the files are read completely before closing
        output = stdout.read().decode()
        error_output = stderr.read().decode()

        print(output)
        if error_output:
            print(f"Error: {error_output}")

    finally:
        # Ensure everything is closed properly
        try:
            stdout.close()
            stderr.close()
        except:
            pass
        client.close()

    # ixnet / globals / stats / advance/ timestamp
    ixnet_session.Statistics.TimestampPrecision = 9
    ixnet_session.info(f"Step {myStep.add()} - Init - Rest Session {session.Session.Id} established.")
    ixnet_session.info(f"Step {myStep.add()} - Init - Enable Use Schedule Start Transmit in Test Options -> Global Settings.")
    #Set Latency Delay Mode to Store and Forward
    ixnet_session.Traffic.Statistics.DelayVariation.LatencyMode = 'storeForward'

    ixnet_session.info(f"Step {myStep.add()} - Init - Assign Ports to Session.")
    port_map = session.PortMapAssistant()
    mySlot, portIndex = TestVars.port1.split("/")
    vport_dic["Grand"] =  port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="GrandMaster")
    mySlot, portIndex = TestVars.port2.split("/")
    vport_dic["Follower"] =port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Follower")
    port_map.Connect(ForceOwnership=TestVars.takePorts,IgnoreLinkUp=True)  
    ixnet_session.info(f"Step {myStep.add()} - Verify -  Checking if all ports are up")
    portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
    boolPortsAreUp = portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up',Timeout=20,RaiseException=False)
    # Setting TX mode to inter-leaved

    if not TestVars.mini_flag:
        for vport in vport_dic:
            thisPort = ixnet_session.Vport.find(Name=vport)
            #thisPort.Type = 'novusTenGigLanFcoe'
            portType = thisPort.Type[0].upper() + thisPort.Type[1:]
            ixnet_session.info(f"Step {myStep.add()} - Init - Setting port {vport} to Interleaved mode")
            thisPort.TxMode = 'interleaved'
            portObj = getattr(thisPort.L1Config, portType)
            #portObj.EnabledFlowControl = False
            if not boolPortsAreUp:
                ixnet_session.info(f" Step {myStep.add_minor()} - Init - Ports are not up trying to change the media")
                if portObj.Media and portObj.Media == 'fiber':
                    portObj.Media = 'copper'
                elif  portObj.Media and portObj.Media == 'copper':
                    portObj.Media = 'fiber'
        # If ports are not up now we are done.....
        if not boolPortsAreUp:
            ixnet_session.info(f"Step {myStep.add()} - Init - Checking once more if all ports are up - Abort otherwise")
            portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30,RaiseException=True)
    
    
    # Setting UP the QBV params in the L1 port level
    _qbv  = ixnet_session.Vport.find(Name='Follower').L1Config.Qbv

    _qbv.IsQbvEnabled = True
    _rxGate = _qbv.RxGateControlList.find()
    _rxGate.UnitOfTime = 'MicroSecond'
    gate_list_to_be_cfg = []
    total_cycle_time_microseconds = 0
    for this_gate in TestVars.gates:
        _gate_list = [this_gate['gate_state'],this_gate['gate_open_microseconds']]
        gate_list_to_be_cfg.append(_gate_list)
        total_cycle_time_microseconds += this_gate['gate_open_microseconds']
    _rxGate.GateControlList = gate_list_to_be_cfg

    # Set Cycle Time Based on input table
    ixnet_session.Traffic.UseScheduledStartTransmit = True
    ixnet_session.info(f"Step {myStep.add()} - Init - Config Cycle Time to {total_cycle_time_microseconds} microSeconds.")
    ixnet_session.Traffic.CycleTimeForScheduledStart = total_cycle_time_microseconds
    ixnet_session.Traffic.CycleTimeUnitForScheduledStart = 'microseconds'
    ixnet_session.info(f"Step {myStep.add()} - Init - Config Global Stats latency to Store and Forward mode.")
    ixnet_session.Traffic.Statistics.Latency.Enabled = True
    ixnet_session.Traffic.Statistics.Latency.update(Mode='storeForward')

    # Calculate the total number of bits in the packet including payload , preamble and IFG
    total_bits = ( TestVars.pktSize_in_bytes * 8 ) + ( TestVars.preamble_in_bytes * 8 ) + ( TestVars.inter_frame_gap_in_bytes * 8 )
    print(f"total_bits includes ( pkt_size in bytes + preamble 8 B  and inter-frame gap 12 B ) * 8 = {total_bits}")
    rate_per_second = TestVars.data_rate_in_Gbps * 1_000_000_000
    tx_rate_per_second = math.floor(rate_per_second / total_bits)
    tx_rate_per_microsecond = tx_rate_per_second / 1_000_000
    pps_per_stream = floor_to_nearest_hundred(tx_rate_per_microsecond * float(total_cycle_time_microseconds))
    print(f"pps_per_stream = {pps_per_stream} - Value shared among all queues")
    num_of_cycle_windows = len(TestVars.gates)
    pps_per_stream = pps_per_stream / num_of_cycle_windows

    # GrandMaster
    ixnet_session.info(f"Step {myStep.add()} - Init - Setting up gPTP GrandMaster Side on port {TestVars.port1}")
    topo1 = ixnet_session.Topology.add(Name='802.1AS Master Topology', Ports=vport_dic["Grand"])
    dev1 = topo1.DeviceGroup.add(Name='GrandMaster - DG', Multiplier='1')
    eth1 = dev1.Ethernet.add(Name='gm_ether')
    eth1.Mac.Single(macs.generate_mac_address())
    gPtpHandle = eth1.Ptp.add(Name='gm_ptp')
    gPtpHandle.Profile.Single(TestVars.gPtp_profile)
    gPtpHandle.Role.Single('master')
    gPtpHandle.StrictGrant.Single(True)

    # Follower
    ixnet_session.info(f"Step {myStep.add()} - Init - Setting up gPTP Follower Side on port {TestVars.port2}")
    topo2 = ixnet_session.Topology.add(Name='802.1AS Follower Topology', Ports=vport_dic["Follower"])
    dev2 = topo2.DeviceGroup.add(Name='Follower - DG', Multiplier='1')
    eth2 = dev2.Ethernet.add(Name='followe_ether')
    eth2.Mac.Single(macs.generate_mac_address())
    gPtpSHandle = eth2.Ptp.add(Name='Follower')
    gPtpSHandle.Profile.Single(TestVars.gPtp_profile)


    ixnet_session.info(f'Step {myStep.add()} - Init -  Staring Protocols')
    ixnet_session.StartAllProtocols(Arg1='sync')
    
    ixnet_session.info(f'Step {myStep.add()} - Verify -  PTP sessions are UP')
    protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
    protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^PTP?')
    protocolsSummary.CheckCondition('Sessions Up', StatViewAssistant.EQUAL, '2')
    protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, '0')

    ixnet_session.info(f'Step {myStep.add()} - Init -  Create Unidirectional Ipv4 Traffic Item')

    # bridge fdb add 00:01:ca:ff:ee:99 dev swp3 master static

    traffic_item = ixnet_session.Traffic.TrafficItem.add(Name='QuickFlow', TrafficType='raw')
    gate_index = 0
    ini_cycle_time = 0
    for this_gate in TestVars.gates:
        traffic_item.EndpointSet.add(
            Sources=ixnet_session.Vport.find(Name='GrandMaster').Protocols.find(),
            Destinations=ixnet_session.Vport.find(Name='Follower').Protocols.find()
        )
        # Configure traffic: rate and total frame count control
        config_element = traffic_item.ConfigElement.find()[gate_index]
        highLevel_stream = traffic_item.HighLevelStream.find()[gate_index]
        flow_name = 'Flow Dst to Gate' + str(gate_index + 1)
        highLevel_stream.Name = flow_name
        config_element.FrameRate.update(Type="framesPerSecond", Rate=int(pps_per_stream))  # 250 pps
        config_element.TransmissionControl.update(Type="fixedFrameCount", FrameCount=1000)
        config_element.FrameSize.FixedSize = 100
        #config_element.TransmissionControl.update(StartDelayUnits='microseconds')
        #config_element.TransmissionControl.update(StartDelay=ini_cycle_time)
        # Ethernet header configuration (use desired MACs)
        ether_stack = config_element.Stack.find(StackTypeId="ethernet")
        ethernetDstField = ether_stack.Field.find(DisplayName='Destination MAC Address')
        ethernetDstField.ValueType = 'increment'
        ethernetDstField.StartValue = "00:01:CA:FF:EE:99"
        ethernetDstField.StepValue = "00:00:00:00:00:00"
        ethernetDstField.CountValue = 1
        ethernetSrcField = ether_stack.Field.find(DisplayName='Source MAC Address')
        ethernetSrcField.ValueType = 'increment'
        ethernetSrcField.StartValue = "00:01:BA:DB:BE:01"
        ethernetSrcField.StepValue = "00:00:00:00:00:00"
        ethernetSrcField.CountValue = 1

        # Add VLAN tag below Ethernet header
        packetHeaderProtocolTemplate = ixnet_session.Traffic.ProtocolTemplate.find(StackTypeId='^vlan$')
        ethernetStackObj = config_element.Stack.find(DisplayName='Ethernet II')
        ethernetStackObj.Append(Arg2=packetHeaderProtocolTemplate)

        vlanObj = config_element.Stack.find(DisplayName='VLAN')
        vlanIdField = vlanObj.Field.find(DisplayName='VLAN-ID')
        vlanIdField.SingleValue = 100

        vlanPriorityField = vlanObj.Field.find(DisplayName='VLAN Priority')
        vlanPriorityField.Auto = False
        vlanPriorityField.ValueType = 'valueList'
        vlanPriorityField.ValueList = this_gate['vlan_pri']

        # Generate, apply, and start traffic
        traffic_item.Generate()

        # Nex Cycle time vars
        ini_cycle_time += this_gate['gate_open_microseconds']
        gate_index += 1

    _egressOnly = ixnet_session.Traffic.EgressOnlyTracking.add(Port = ixnet_session.Vport.find(Name='Follower').href, Enabled = True)
    _egressOnly.SignatureLengthType = 'fourByte'
    _egressOnly.SignatureMask = '00 00 00 00'
    _egressOnly.SignatureOffset = 10
    _egressOnly.SignatureValue = 'be 01 81 00'


    new_egress = [
        {"arg1": 14, "arg2": "1F FF FF FF"},
        {"arg1": 52, "arg2": "FF FF FF FF"},
        {"arg1": 52, "arg2": "FF FF FF FF"}
    ]
    _egressOnly.Egress = new_egress

    new_qbv = [
        {"arg1": True, "arg2": 1, "arg3": True, "arg4": "0-3"},
        {"arg1": True, "arg2": 2, "arg3": False, "arg4": "4"},
        {"arg1": True, "arg2": 3, "arg3": False, "arg4": "5"},
        {"arg1": True, "arg2": 4, "arg3": False, "arg4": "6-7"},
        {"arg1": False, "arg2": 5, "arg3": False, "arg4": "4"},
        {"arg1": False, "arg2": 6, "arg3": False, "arg4": "5"},
        {"arg1": False, "arg2": 7, "arg3": False, "arg4": "6"},
        {"arg1": False, "arg2": 8, "arg3": False, "arg4": "7"}
    ]

    _egressOnly.QbvSettings = new_qbv

    ixnet_session.Traffic.EnableEgressOnlyTracking = True

    view = ixnet_session.Statistics.View.find(Caption='^Qbv Gate Statistics$')
    view.Enabled = True
    time.sleep(10)
    ixnet_session.Traffic.Apply()
    ixnet_session.info(f'Step {myStep.add()} - Test - Send Traffic - \n### NOTE WE EXPECT THIS TO FAIL AS Ixia is NOT sending schedueled traffic')
    ixnet_session.info(f'Step {myStep.add()} - Test - Send Traffic - AND THERES IS NOT QBV CONFIGURATION ON THE DUT EGRESS PORT ###\n')
    
    ixnet_session.Traffic.Start()  
    time.sleep(20)
    ixnet_session.Traffic.Stop()  
    checkTrafficState(ixnet_session, state= 'stopped')
    time.sleep(10)

    # CHeck #1 -- All Traffic went thru
    ixnet_session.info(f'Step {myStep.add()} - Verify - All traffic sent was received')
    traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')
    traffItemStatistics.AddRowFilter('Traffic Item', StatViewAssistant.REGEX, 'Quick Flow Groups Egress Only')
    for flowStat in traffItemStatistics.Rows: 
        if int(flowStat['Rx Frames']) == 4000:
            ixnet_session.info(f"Rx Frames {int(flowStat['Rx Frames']):,} -- PASS")
        else:
            ixnet_session.info(f"Rx Frames {int(flowStat['Rx Frames']):,} --  Expecting 4,000 --- FAILED")

    resultsDict = dict()
    flowGrpStatistics = StatViewAssistant(ixnet_session, 'Qbv Gate Statistics')
    flowGrpStatistics.AddRowFilter('Port Name', StatViewAssistant.REGEX, '^Follower$')
    for flowStat in flowGrpStatistics.Rows:
        gate_id = flowStat['Gate']
        resultsDict[gate_id] = dict()
        resultsDict[gate_id]['valid'] = flowStat['Window Valid Frame Count']
        resultsDict[gate_id]['invalid'] = flowStat['Window Violation Frame Count']

    for gate_id, values in resultsDict.items():
        valid_count = int(values['valid'])
        invalid_count = int(values['invalid'])
        if int(gate_id) < 5:
            if valid_count == 1000 and invalid_count == 0:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- OK")
            else:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- OK") 
        else:
            if valid_count == 0 and invalid_count == 0:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- OK")
            else:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- OK")        
        
    # In Order to FIX this we can 
    # 1) Adjust the start delay per stream to match the cycle time windows using Ixia
    # 2) Add the QBV settings in the Egress port on the DUT side.
    ixnet_session.info(f"\n**** Lets Apply QBV on the DUT's Egress Port and rerun the test****\n")
    try:
        # Reboot the server and reconnect
        client = dut_connect(TestVars.dut_ip, TestVars.dut_username, TestVars.dut_password)
        time.sleep(10)
        print("Running Qbv setup...")
        stdin, stdout, stderr = client.exec_command("./qbv/set_qbv_1ms_4q.sh")
        time.sleep(10)
        # Ensure the files are read completely before closing
        output = stdout.read().decode()
        error_output = stderr.read().decode()

        print(output)
        if error_output:
            print(f"Error: {error_output}")

    finally:
        # Ensure everything is closed properly
        try:
            stdout.close()
            stderr.close()
        except:
            pass
        client.close()
    
    time.sleep(60)
    ixnet_session.info(f'Step {myStep.add()} - Test - Send Traffic')
    ixnet_session.Traffic.Start()  
    time.sleep(20)
    ixnet_session.Traffic.Stop()  
    checkTrafficState(ixnet_session, state= 'stopped')
    time.sleep(10)

    # CHeck #1 -- All Traffic went thru
    ixnet_session.info(f'Step {myStep.add()} - Verify - All traffic sent was received')
    traffItemStatistics = StatViewAssistant(ixnet_session, 'Traffic Item Statistics')
    traffItemStatistics.AddRowFilter('Traffic Item', StatViewAssistant.REGEX, 'Quick Flow Groups Egress Only')
    for flowStat in traffItemStatistics.Rows: 
        if int(flowStat['Rx Frames']) == 4000:
            ixnet_session.info(f"Rx Frames {int(flowStat['Rx Frames']):,} -- PASS")
        else:
            ixnet_session.info(f"Rx Frames {int(flowStat['Rx Frames']):,} --  Expecting 4,000 --- FAILED")

    resultsDict = dict()
    flowGrpStatistics = StatViewAssistant(ixnet_session, 'Qbv Gate Statistics')
    flowGrpStatistics.AddRowFilter('Port Name', StatViewAssistant.REGEX, '^Follower$')
    for flowStat in flowGrpStatistics.Rows:
        gate_id = flowStat['Gate']
        resultsDict[gate_id] = dict()
        resultsDict[gate_id]['valid'] = flowStat['Window Valid Frame Count']
        resultsDict[gate_id]['invalid'] = flowStat['Window Violation Frame Count']

    for gate_id, values in resultsDict.items():
        valid_count = int(values['valid'])
        invalid_count = int(values['invalid'])
        if int(gate_id) < 5:
            if valid_count == 1000 and invalid_count == 0:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- PASS")
            else:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- FAIL Expecting 1,000 valid and 0 invalid") 
        else:
            if valid_count == 0 and invalid_count == 0:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- PASS")
            else:
                ixnet_session.info(f"Gate ID {gate_id} - Valid Frames: {valid_count:,}, Invalid Frames: {invalid_count:,} -- FAIL Expecting 0 valid and 0 invalid")  

    # Clean up
    ixnet_session.info(f'Step {myStep.add()} - Clean up - Stopping all protocols ')
    ixnet_session.StopAllProtocols()        
    if TestVars.sessionId == None:
        ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Removing Session we created...bye")
        session.Session.remove()
    else: 
        ixnet_session.info(f"Step {myStep.add_minor()} - Clean up - Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()
    ixnet_session.info(f"Step {myStep.add()} - Clean up - The End")

if __name__ == '__main__':
    main()  
