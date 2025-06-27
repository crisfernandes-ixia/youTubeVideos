from ixnetwork_restpy import *
import time
import traceback
import os

"""

"""

class testVars: pass


import random

import random

def compare_numbers(num1, num2, threshold : float = 0.98) -> bool :
    difference = abs(num1 - num2)
    avg = (num1 + num2) / 2
    percent_difference = difference / avg
    if percent_difference <= (1 - threshold):
        return True
    return False

def main():
    TestVars = testVars()
    # description
    TestVars.chassisIp : str = '10.80.81.2'
    TestVars.sessionIp : str = 'localhost'
    TestVars.sessionId : str = 1
    TestVars.user : str      = 'cris'
    TestVars.cleanConfig : bool = True
    TestVars.password: str   =  'Keysight#12345'
    TestVars.txPort : str   = '2/1'
    TestVars.rxPort : str    = '2/2'
    outLogFile : str = 'addPorts_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
    session = None

    if TestVars.sessionId == 'None':
        TestVars.sessionId = None

    try:
        session = SessionAssistant(IpAddress='localhost',
                                   UserName="",
                                   Password="",
                                   SessionId=1,
                                   ClearConfig=True,
                                   LogLevel='info',
                                   LogFilename=outLogFile)

    except ConnectionError as conn_err:
        print(f"Connection error: Unable to reach the TestPlatform at localserver")
        print(f"Details: {conn_err}")
    except UnauthorizedError as auth_err:
        print("Authentication failed: Unauthorized access.")
        print(f"Details: {auth_err}")
    except NotFoundError as not_found_err:
        print(f"Session ID not found on the test platform: id")
        print(f"Details: {not_found_err}")
    except ValueError as value_err:
        print(f"Unsupported IxNetwork server version. Minimum version supported is 8.42.")
        print(f"Details: {value_err}")
    except Exception as errMsg:
        # General exception handling for any other unhandled exceptions
        print("An unexpected error occurred:")

    ixnet_session = session.Ixnetwork

    ixnet_session.info(f"Step#1 - Init - Rest Session {session.Session.Id} established.")
    vport_dic = dict()

    ### LEARN BIT PORTMAPASSISTANT
    port_map = session.PortMapAssistant()
    mySlot, portIndex = TestVars.txPort.split("/")
    vport_dic["Port1"] = port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Port1")
    mySlot, portIndex = TestVars.rxPort.split("/")
    vport_dic["Port2"] = port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Port2")

    try:
        port_map.Connect(ForceOwnership=True, IgnoreLinkUp=True)
    except Exception:
        traceback.print_exc()

    port_stats = StatViewAssistant(ixnet_session, 'Port Statistics')
    boolPortsAreUp = port_stats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=30, RaiseException=False)
    if not boolPortsAreUp:
        for vport in ixnet_session.Vport.find():
            portType = vport.Type[0].upper() + vport.Type[1:]
            portObj = getattr(vport.L1Config, portType)
            if portObj.Media and portObj.Media == 'fiber':
                portObj.update(Media = 'copper')
            else:
                portObj.Media = 'fiber'
        port_stats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=20, RaiseException=False)


    ixnet_session.info('Creating Topology Group 1 - Clients')
    topology1 = ixnet_session.Topology.add(Name='Clients', Ports=vport_dic['Port1'])
    deviceGroup1 = topology1.DeviceGroup.add(Name='CLIENTS', Multiplier='5')
    ethernet1 = deviceGroup1.Ethernet.add(Name='Eth1')
    ethernet1.Mac.Increment(start_value='00:CA:FF:EE:00:01', step_value='00:00:00:00:00:01')
    ethernet1.EnableVlans.Single(True)
    ixnet_session.info('Configuring vlanID')
    ethernet1.Vlan.find()[0].VlanId.Increment(start_value=100, step_value=0)

    ixnet_session.info('Configuring IPv4')
    clients_ipv4 = ethernet1.Ipv4.add(Name='Ipv4')
    clients_ipv4.Address.Increment(start_value='172.16.1.1', step_value='0.0.0.1')
    clients_ipv4.GatewayIp.Single('172.16.1.254')

    ixnet_session.info('Creating Topology Group 2 - Server')
    topology2 = ixnet_session.Topology.add(Name='Server_Topo', Ports=vport_dic['Port2'])
    deviceGroup2 = topology2.DeviceGroup.add(Name='SERVER', Multiplier='1')
    ethernet2 = deviceGroup2.Ethernet.add(Name='Eth2')
    ethernet2.Mac.Increment(start_value='00:BA:D0:BE:EF:F1', step_value='00:00:00:00:00:00')
    ethernet2.EnableVlans.Single(True)
    ethernet2.Vlan.find()[0].VlanId.Increment(start_value=100, step_value=0)

    ixnet_session.info('Configuring IPv4')
    server_ipv4 = ethernet2.Ipv4.add(Name='Ipv4')
    server_ipv4.Address.Single('172.16.1.254')
    server_ipv4.GatewayIp.Increment(start_value='172.16.1.1', step_value='0.0.0.1')

    ixnet_session.info(f'Test Phase - Step 1: Staring Protocols - Control Plane messages')
    ixnet_session.StartAllProtocols(Arg1='sync')
    protocolsSummary = StatViewAssistant(ixnet_session, 'Protocols Summary')
    protocolsSummary.AddRowFilter('Protocol Type', StatViewAssistant.REGEX, '(?i)^IPv4?')
    protocolsSummary.CheckCondition('Sessions Down', StatViewAssistant.EQUAL, 0)
    protocolsSummary.CheckCondition('Sessions Not Started', StatViewAssistant.EQUAL, 0)


    ixnet_session.info('Test Phase - Step 4: Create Unidirectional Traffic Item')
    #'trafficType': ['atm', 'avb1722', 'avbRaw', 'ethernetVlan', 'fc', 'fcoe', 'frameRelay', 'hdlc', 'ipv4',
    #                'ipv4ApplicationTraffic', 'ipv6', 'ipv6ApplicationTraffic', 'ppp', 'raw'],
    traff_item_server_to_clients = ixnet_session.Traffic.TrafficItem.add(Name='Server to Clients', BiDirectional=False,TrafficType='ipv4')
    config_elem_dict = {}
    traff_item_server_to_clients.EndpointSet.add(Sources=server_ipv4, Destinations=clients_ipv4)
    traff_item_server_to_clients.EndpointSet.add(Sources=server_ipv4, Destinations=clients_ipv4)
    traff_item_server_to_clients.EndpointSet.add(Sources=server_ipv4, Destinations=clients_ipv4)
    traff_item_server_to_clients.EndpointSet.add(Sources=clients_ipv4, Destinations=server_ipv4)
    

    config_elem_1 = traff_item_server_to_clients.ConfigElement.find()[0]
    config_elem_2 = traff_item_server_to_clients.ConfigElement.find()[1]
    config_elem_3 = traff_item_server_to_clients.ConfigElement.find()[2]
    config_elem_4 = traff_item_server_to_clients.ConfigElement.find()[3]
    
    
    # Type: percentLineRate / bitsPerSecond / framesPerSecond / interPacketGap
    config_elem_1.FrameRate.update(Type='percentLineRate', Rate=30)
    config_elem_2.FrameRate.update(Type='framesPerSecond', Rate=1000)
    config_elem_3.FrameRate.update(Type='bitsPerSecond', Rate=100_000)
    config_elem_1.FrameSize.FixedSize = 100
    config_elem_2.FrameSize.FixedSize = 200
    config_elem_3.FrameSize.FixedSize = 300
    config_elem_4.FrameSize.FixedSize = 64

    traff_item_server_to_clients.Generate()
    traff_item_server_to_clients.Tracking.find()[0].TrackBy = ["trackingenabled0", "ipv4DestIp0"]
    traff_item_server_to_clients.Generate()
    ixnet_session.Traffic.Apply()

    # LEARN BIT
    ixnet_session.Traffic.EnableMinFrameSize = True
    ixnet_session.Traffic.find().MinimumSignatureLength = 4
    ixnet_session.Traffic.Apply()
    traff_item_server_to_clients.Generate()
    ixnet_session.Traffic.Apply()
    ixnet_session.Traffic.Start()

    ixnet_session.info('Test Phase - Step 5: Let traffic run for 20 seconds')
    time.sleep(20)

    ## LEARN BIT
    # What can we do while the traffic is running - ? Rate and Size changes
    ixnet_session.info('Test Phase - Step 6: Changing traffic item configuration')
    config_elem_1_dynamicFrameSize = ixnet_session.Traffic.DynamicFrameSize.find()[0]
    config_elem_1_dynamicFrameSize.FixedSize = 1280
    
    config_elem_2_dynamicRate = ixnet_session.Traffic.DynamicRate.find()[1]
    config_elem_2_dynamicRate.update(RateType='percentLineRate')
    config_elem_2_dynamicRate.update(Rate=50)


    ixnet_session.info('Test Phase - Step 6: Collecting traffic item statistics and printing L1 Rate stats')
    flowStatistics = session.StatViewAssistant('Traffic Item Statistics')
    for rowNumber, flowStat in enumerate(flowStatistics.Rows):
        ixnet_session.info(f"Test Phase - Step 7: Traffic Item:{flowStat['Traffic Item']} TX L1 Rate:{float(flowStat['Tx L1 Rate (bps)']):,} RX L1 Rate:{float(flowStat['Rx L1 Rate (bps)']):,}\n")
        time.sleep(10)

    # Stop Traffic 
    ixnet_session.Traffic.Stop()

    # Check Traffic State
    while True:
        if ixnet_session.Traffic.State == 'stopped':
            break
        ixnet_session.info(f"Traffic State {ixnet_session.Traffic.State}")
        time.sleep(2)

    # Get Stats
    resultsDict = dict()
    flowGrpStatistics = StatViewAssistant(ixnet_session, 'Flow Statistics')
    flowGrpStatistics.AddRowFilter('Tx Port', StatViewAssistant.REGEX, 'Port2')
    for flowStat in flowGrpStatistics.Rows:
             queueId = flowStat['IPv4 :Destination Address']
             resultsDict[queueId] = dict()
             resultsDict[queueId]['TX'] = flowStat['Tx Frames']
             resultsDict[queueId]['RX'] = flowStat['Rx Frames']

    for queueId, stats in resultsDict.items():
        txFrames = float(stats['TX'])
        rxFrames = float(stats['RX'])
        ixnet_session.info(f"QueueId:{queueId} TX Frames:{txFrames:,} RX Frames:{rxFrames:,}")
        if txFrames == 0:
            ixnet_session.info(f"QueueId:{queueId} - No traffic sent, skipping comparison")
            continue
        if compare_numbers(txFrames,rxFrames):
            ixnet_session.info(f"QueueId:{queueId} - Test PASS")
        else:
            ixnet_session.info(f"QueueId:{queueId} - Test FAILED")            


    # Stopping Protocols
    ixnet_session.StopAllProtocols()
    time.sleep(10)

    # Release all ports
    ixnet_session.Vport.find().ReleasePort()

    # Disconnect from the session
    if TestVars.sessionId == None:
        ixnet_session.info(f"Removing Session we created...bye")
        session.Session.remove()
    else:
        ixnet_session.info(f"Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()


if __name__ == "__main__":
    main()

