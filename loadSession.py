from ixnetwork_restpy import *
import time
import traceback
import os
import random

"""
_Load A saved Config file 
- Ports Are called Port1 and Port2 
- There is traffic
"""


class testVars: pass

def main():
    TestVars = testVars()
    # description
    TestVars.chassisIp: str = '10.80.81.2'
    TestVars.sessionIp: str = 'localhost'
    TestVars.sessionId: str = 1
    TestVars.user: str = 'cris'
    TestVars.cleanConfig: bool = True
    TestVars.password: str = 'Keysight#12345'
    TestVars.txPort: str = '4/1'
    TestVars.rxPort: str = '4/2'
    outLogFile: str = 'loadSession_' + time.strftime("%Y%m%d-%H%M%S") + '.log'
    savedFile: str = 'loadSessionWithPorts_v1.ixncfg'

    # Initialize session handle like the good old days of C and C++
    session = None

    if TestVars.sessionId == 'None':
        TestVars.sessionId = None

    try:
        session = SessionAssistant(IpAddress=TestVars.sessionIp,
                                   UserName=TestVars.user,
                                   Password=TestVars.password,
                                   SessionId=TestVars.sessionId,
                                   ClearConfig=TestVars.cleanConfig,
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
    ixnet_session.info(f'Loading config file: {savedFile}')
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), savedFile)
    file_path_temp = file_path.replace(".ixncfg",  "_" + TestVars.user + '.ixncfg')
    # Loading the original file
    ixnet_session.LoadConfig(Files(file_path, local_file=True))
    ixnet_session.info(f"Original File: {file_path} uploaded.")
    ixnet_session.SaveConfig(Files(file_path_temp, local_file=True))
    ixnet_session.info(f"Saving as temp since we are making changes: {file_path_temp}")

    # LESS FLEXIBLE BUT FASTER
    vport_dic = dict()

    ### LEARN BIT -- NAME HERE IS VERY IMPORTANT
    #if you don't know the name there are a few things you can do.
    # - You can rename the ports or grab the name from the config
    ## Grabbing the name.
    list_names = []
    for vport_handle in ixnet_session.Vport.find():
        list_names.append(vport_handle.Name)

    # Rename them before Mapping them.
    for index, vport_handle in enumerate(ixnet_session.Vport.find(), start=1):
        vport_handle.Name = 'Port' + str(index)

    # IF you know the port name it is easy and by addin the name here it will replace the ports.
    port_map = session.PortMapAssistant()
    mySlot, portIndex = TestVars.txPort.split("/")
    vport_dic["Port1"] = port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Port1")
    mySlot, portIndex = TestVars.rxPort.split("/")
    vport_dic["Port2"] = port_map.Map(TestVars.chassisIp, mySlot, portIndex, Name="Port2")

    '''
        Examples
        --------
            Map(IpAddress='10.36.74.26', CardId=2, PortId=13, Name='Tx')
            Map(Name='Tx', Port=('10.36.74.26', 2, 13))
            Map('10.36.74.26', 2, 13, Name='Tx')
            Map('10.36.74.26', 2, 14, Name=vport.Name)
            Map(Location='10.36.74.26;1;1', Name='Tx')
            Map(Location='localuhd/1', Name='Tx')

        Args
        ----
        - IpAddress (str): The ip address of the platform that hosts the card/port combination.
            If the IpAddress is not specified the default value is 127.0.0.1
        - CardId (number): The id of the card that hosts the port
            If the CardId is not specified the default value is 1
        - PortId (number): The id of the port.
        - Name (str): The name of a virtual port.
            If the Name is not specified a default named virtual port will be created.
            If the Name is specified an attempt to find it will be made.
            If it does not exist a virtual port with that name will be created.
            The found or created vport will then be mapped.
        - Port (tuple(IpAddress,CardId,PortId)): A test port location tuple consisting of an IpAddress, CardId, PortId.
            Use this parameter instead of specifying the individual IpAddress, CardId, PortId parameters.
            If this parameter is not None it will override any IpAddress, CardId, PortId parameter values.
        - Location (str): A test port location using the new 9.10 location syntax
            The location syntax for test ports can be discovered by using the /locations API
            If this parameter is not None it will override any IpAddress, CardId, PortId, Port parameter values

        Returns
        -------
        - obj(ixnetwork_restpy.testplatform.sessions.ixnetwork.vport.vport.Vport): A Vport object

        Raises
        ------
        - ValueError: a PortId was not provided
        - RuntimeError: Location API is not supported on the server
        - ServerError: an unexpected error occurred on the server
        """
    
    '''



    ### FORCEOWNERSHIP
    port_map.Connect()
    portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
    portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up')

    # Optional Clean up the non used Chassis
    for this_chassis in ixnet_session.AvailableHardware.find().Chassis.find():
        if this_chassis.StateV2 == 'notConnected':
            ixnet_session.info(f"Hostname {this_chassis.Hostname} not connected -- Removing it from session")
            this_chassis.remove()


    # Release all ports
    ixnet_session.Vport.find().ReleasePort()

    if TestVars.sessionId == None:
        ixnet_session.info(f"Removing Session we created...bye")
        session.Session.remove()
    else:
        ixnet_session.info(f"Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()

if __name__ == "__main__":
    main()

