from ixnetwork_restpy import *
import time
import traceback
import os

"""
Map a test port to a virtual port

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
        

        Connect virtual ports to test ports

        Args
        ----
        - ForceOwnership (bool): Forcefully clear ownership of the test ports
        - HostReadyTimeout (bool): The number of seconds to wait for all
            test port hosts to achieve a state of 'ready'
        - LinkUpTimeout (int): The number of seconds to wait for all
            virtual port links to achieve a state of 'Link Up'

        Raises
        ------
        - obj(ixnetwork_restpy.errors.NotFoundError): the HostReadyTimeout or LinkUpTimeout value has been exceeded
        - obj(ixnetwork_restpy.errors.ServerError): an unexpected error occurred on the server
"""

class testVars: pass

def main():
    TestVars = testVars()
    # description
    TestVars.chassisIp : str = '10.80.81.2'
    TestVars.sessionIp : str = 'localhost'
    TestVars.sessionId : str = 1
    TestVars.user : str      = 'cris'
    TestVars.cleanConfig : bool = True
    TestVars.password: str   =  'Keysight#12345'
    TestVars.txPort : str   = '4/1'
    TestVars.rxPort : str    = '4/2'
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

    ### LEARN BIT STATVIEW
    portStats = StatViewAssistant(ixnet_session, 'Port Statistics')
    #### LEARN BIT CHECK CONDITION
    boolPortsAreUp = portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=20,
                                              RaiseException=False)

    ## LEARN BIT FIND
    ### LEARN BIT PORTS L1
    ### LEARNED BIT UPDATE OR =
    if not boolPortsAreUp:
        for vport in ixnet_session.Vport.find():
            portType = vport.Type[0].upper() + vport.Type[1:]
            portObj = getattr(vport.L1Config, portType)
            if portObj.Media and portObj.Media == 'fiber':
                portObj.update(Media = 'copper')
            else:
                portObj.Media = 'fiber'
        portStats.CheckCondition('Link State', StatViewAssistant.REGEX, 'Link\s+Up', Timeout=20, RaiseException=False)

    ## How to find a port handle
    port1_handle = ixnet_session.Vport.find(Name='Port1')
    port2 = ixnet_session.Vport.find(Name='Port2')



    if TestVars.sessionId == None:
        ixnet_session.info(f"Removing Session we created...bye")
        session.Session.remove()
    else:
        ixnet_session.info(f"Cleaning up session and leaving it up...bye")
        ixnet_session.NewConfig()


if __name__ == "__main__":
    main()

