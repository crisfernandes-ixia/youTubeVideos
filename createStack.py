from ixnetwork_restpy import *
import time
import traceback
import os

"""

"""

class testVars: pass


import random

import random

def generate_unique_network_ipv4_addresses(n):
    ip_set = set()

    while len(ip_set) < n:
        first_octet = random.randint(172, 195)
        second_octet = random.randint(0, 255)
        third_octet = random.randint(0, 255)

        network_id = (first_octet, second_octet, third_octet)

        if network_id not in ip_set:
            ip_set.add(network_id)

    # Format all as IP addresses ending in .1 with /24 mask
    ip_list = [f"{a}.{b}.{c}.1" for a, b, c in ip_set]
    return ip_list


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
    ethernet1.Vlan.find()[0].VlanId.Increment(start_value=100, step_value=10)

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

    ## LEARNING BITS
    _handle_for_topolgy = ixnet_session.Topology.find(Name = 'Clients')

    resolvedMacs = ethernet2.find().Ipv4.find().ResolvedGatewayMac

    # LEARN BIT - Global versus per device
    unique_ips = generate_unique_network_ipv4_addresses(5)
    clients_ipv4.Address.ValueList(unique_ips)
    ixnet_session.Globals.Topology.ApplyOnTheFly()


    if TestVars.sessionId == None:
        ixnet_session.info(f"Removing Session we created...bye")
        session.Session.remove()
    else:
        ixnet_session.info(f"Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()


if __name__ == "__main__":
    main()

