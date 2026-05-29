import os
import time
import re
import traceback
import datetime
from ixnetwork_restpy import TestPlatform, SessionAssistant, Files

# Import custom classes from helper (ensure helper.py is in the same directory)
from helper import Step, testVars 

# ==========================================
# Configuration Setup
# ==========================================
TestVars = testVars()
TestVars.sessionIp = '10.80.81.117'
TestVars.chassisIp = '10.80.81.117'
TestVars.username = 'admin'
TestVars.password = 'IxNetwork2022!'
TestVars.configFile = 'baseLineQuickTest.ixncfg'

# Port Mapping Configuration
TestVars.src_port_list = ['4.1', '4.2']
TestVars.dst_port_list = ['1.1', '2.1']
TestVars.forceTakePortOwnership = True

# Session Cleanup Variables
TestVars.cleanup_anyOtherAutoQk = True
TestVars.session_prefix_to_clean = 'AutoQk_'

# Specify the local destination folder for downloaded results
TestVars.results_dir = os.path.join(os.getcwd(), 'QuickTest_Results')

# ==========================================
# Helper Functions
# ==========================================
def generate_autoqk_name():
    """
    Generates a unique string based on the current date and time.
    Target Format: AutoQk_MonDay_H_M (e.g., AutoQk_May28_9_44)
    """
    now = datetime.datetime.now()
    month_day = now.strftime("%b%d")
    hour = str(now.hour)
    minute = now.strftime("%M")
    return f"AutoQk_{month_day}_{hour}_{minute}"

def verify_ngpf_is_layer3(ixNetwork, topology_name, myStep):
    """
    Verifies if the NGPF topology has an IPv4 or IPv6 stack configured.
    """
    try:
        topology = ixNetwork.Topology.find(Name=topology_name)
        if len(topology) == 0: return False
        device_group = topology.DeviceGroup.find()
        if len(device_group) == 0: return False
        ethernet = device_group.Ethernet.find()
        if len(ethernet) == 0: return False
            
        ipv4 = ethernet.Ipv4.find()
        ipv6 = ethernet.Ipv6.find()
        
        is_layer_3 = len(ipv4) > 0 or len(ipv6) > 0
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Topology '{topology_name}' isLayer3: {is_layer_3}")
        return is_layer_3
    except Exception as e:
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Exception verifying topology '{topology_name}': {e}")
        return False

def verify_quick_test_initialization(ixNetwork, qt, myStep):
    """
    Waits for the Quick Test to finish applying and start transmitting.
    """
    apply_counter = 60
    success_states = ['TransmittingComplete', 'TransmittingFrames', 'WaitingForStats', 'CollectingStats', 'TestEnded']
    
    for counter in range(1, apply_counter + 1):
        actions = qt.Results.CurrentActions
        current_action = actions[-1]['arg2'] if actions else 'ApplyingAndInitializing'
        
        if current_action == 'TestEnded':
            raise Exception(f"QuickTest failed during initialization. Status: {qt.Results.Status}")
            
        if current_action in success_states:
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Initialization complete. State: {current_action}")
            break
            
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Initializing ({counter}/{apply_counter}). Current State: {current_action}")
        time.sleep(2)
        
        if counter == apply_counter:
            raise Exception(f"Quick Test stuck on {current_action} during initialization.")

def monitor_quick_test_progress(ixNetwork, qt, myStep, interval=10):
    """
    Monitors the test until completion.
    """
    is_running_break_flag = 0
    traffic_started_flag = False
    
    while True:
        is_running = qt.Results.IsRunning
        progress = qt.Results.Progress
        
        if is_running:
            if not re.match('^Trial.*', str(progress)):
                ixNetwork.info(f"Step {myStep.add_minor():.1f} - Waiting for trial iterations to begin...")
                time.sleep(2)
            else:
                traffic_started_flag = True
                ixNetwork.info(f"Step {myStep.add_minor():.1f} - Running: {progress}")
                time.sleep(interval)
        else:
            if traffic_started_flag:
                ixNetwork.info(f"Step {myStep.add()} - Quick Test execution complete.")
                break
                
            if is_running_break_flag < 20:
                ixNetwork.info(f"Step {myStep.add_minor():.1f} - Test not running yet. Waiting...")
                is_running_break_flag += 1
                time.sleep(2)
            else:
                raise Exception(f"Quick Test failed to start running. Status: {qt.Results.Status}")

def download_linux_results(session, ixNetwork, qt, test_name, myStep):
    """
    Downloads the CSV files and generates/downloads the PDF directly.
    """
    result_path = qt.Results.ResultPath
    files_to_get = ['AggregateResults.csv', 'iteration.csv', 'results.csv', 'portMap.csv']
    
    for file in files_to_get:
        remote_file = f"{result_path}/{file}" 
        local_file = os.path.join(TestVars.results_dir, f"{test_name}_{file}")
        try:
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Downloading {file}...")
            session.Session.DownloadFile(remote_file, local_file)
        except Exception as e:
            ixNetwork.warn(f"Could not download {file}. Error: {e}")
            
    try:
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Generating PDF Report...")
        pdf_path = qt.GenerateReport()
        if pdf_path:
            local_pdf = os.path.join(TestVars.results_dir, f"{test_name}_Report.pdf")
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Downloading PDF to {local_pdf}")
            session.Session.DownloadFile(pdf_path, local_pdf)
    except Exception as e:
         ixNetwork.warn(f"PDF generation failed or is not supported for this test type: {e}")

# ==========================================
# Main Execution
# ==========================================
def main():
    myStep = Step()
    
    if not os.path.exists(TestVars.results_dir):
        os.makedirs(TestVars.results_dir)

    try:
        # ----------------------------------------------------
        # Pre-Flight Session Cleanup
        # ----------------------------------------------------
        if TestVars.cleanup_anyOtherAutoQk:
            print(f"Step {myStep.add()} - Checking API server for stale sessions...")
            try:
                platform = TestPlatform(TestVars.sessionIp)
                platform.Authenticate(TestVars.username, TestVars.password)
                sessions = platform.Sessions.find()
                
                cleaned_count = 0
                for s in sessions:
                    if s.Name and s.Name.startswith(TestVars.session_prefix_to_clean):
                        print(f"Step {myStep.add_minor():.1f} - Purging old session: {s.Name} (ID: {s.Id})")
                        s.remove()
                        cleaned_count += 1
                        
                if cleaned_count == 0:
                    print(f"Step {myStep.add_minor():.1f} - No stale '{TestVars.session_prefix_to_clean}' sessions found.")
            except Exception as e:
                print(f"Step {myStep.add_minor():.1f} - Warning: Cleanup encountered an issue: {e}")


        # ----------------------------------------------------
        # Connect & Initialize New Session
        # ----------------------------------------------------
        print(f"Step {myStep.add()} - Connecting to IxNetwork Web/Linux API Server at {TestVars.sessionIp}")
        session = SessionAssistant(IpAddress=TestVars.sessionIp,
                                   UserName=TestVars.username,
                                   Password=TestVars.password,
                                   ApplicationType='quicktest',
                                   ClearConfig=True,
                                   LogLevel='info')
        
        ixNetwork = session.Ixnetwork
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Rest Session {session.Session.Id} established.")
        
        # Rename the session dynamically
        _new_name = generate_autoqk_name()
        session.Session.Name = _new_name
        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Re-Named session to {_new_name}")
        
        ixNetwork.info(f"Step {myStep.add()} - Loading configuration: {TestVars.configFile}")
        ixNetwork.LoadConfig(Files(TestVars.configFile, local_file=True))
        
        # ----------------------------------------------------
        # Port Mapping Validation and Application
        # ----------------------------------------------------
        ixNetwork.info(f"Step {myStep.add()} - Validating and Mapping Ports")
        vports = ixNetwork.Vport.find()
        _num_ports_expected = len(vports)
        _num_ports_configured = len(TestVars.src_port_list) + len(TestVars.dst_port_list)
        
        if _num_ports_expected != _num_ports_configured:
            ixNetwork.info(f"CRITICAL: Mismatch between config ports ({_num_ports_expected}) and target ports ({_num_ports_configured}).")
            session.Session.remove()
            exit()

        vport_index = 0
        portMap = session.PortMapAssistant()
        
        for port in TestVars.src_port_list:
            _vport = vports[vport_index]
            _this_port_name = 'src_port_' + port
            _location = TestVars.chassisIp + '/' + port
            _vport.Name = _this_port_name
            portMap.Map(Location=_location, Name=_this_port_name)
            vport_index += 1

        for port in TestVars.dst_port_list:
            _vport = vports[vport_index]
            _this_port_name = 'dst_port_' + port
            _location = TestVars.chassisIp + '/' + port
            _vport.Name = _this_port_name
            portMap.Map(Location=_location, Name=_this_port_name)
            vport_index += 1

        ixNetwork.info(f"Step {myStep.add_minor():.1f} - Connecting Port Map to Chassis (ForceOwnership={TestVars.forceTakePortOwnership})")
        portMap.Connect(TestVars.forceTakePortOwnership)

        # ----------------------------------------------------
        # NGPF Protocol Verification
        # ----------------------------------------------------
        ixNetwork.info(f"Step {myStep.add()} - Checking NGPF Topologies for Layer 3 Protocols")
        topology_list = ixNetwork.Topology.find()
        is_layer3_present = False
        
        for topology in topology_list:
            if verify_ngpf_is_layer3(ixNetwork, topology.Name, myStep):
               is_layer3_present = True

        if is_layer3_present:
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Layer 3 topologies detected. Starting all protocols (sync).")
            ixNetwork.StartAllProtocols(Arg1='sync')

            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Verifying protocol sessions via StatViewAssistant...")
            protocolSummary = session.StatViewAssistant('Protocols Summary', Timeout=30)
            protocolSummary.CheckCondition('Sessions Not Started', protocolSummary.EQUAL, 0, Timeout=30, RaiseException=False)
            protocolSummary.CheckCondition('Sessions Down', protocolSummary.EQUAL, 0, Timeout=30, RaiseException=False)
            ixNetwork.info(protocolSummary)
        else:
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - No Layer 3 topologies found. Skipping protocol start.")

        # ----------------------------------------------------
        # Target only RFC2544 Throughput Tests
        # ----------------------------------------------------
        ixNetwork.info(f"Step {myStep.add()} - Searching for RFC2544 Throughput Tests")
        rfc2544_tests = ixNetwork.QuickTest.Rfc2544throughput.find()
        
        if len(rfc2544_tests) == 0:
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - No RFC2544 Throughput tests found in the loaded config. Exiting.")
            session.Session.remove()
            return

        for qt in rfc2544_tests:
            test_name = qt.Name.replace(' ', '_')
            ixNetwork.info(f"Step {myStep.add()} - Executing RFC2544 Throughput Test: {test_name}")

            # 1. Allow the chassis/DUT a moment to resolve ARP/NDP
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Allowing protocols to fully settle (15s)...")
            time.sleep(15)

            # 2. REGENERATE TRAFFIC: Bind the saved traffic items to the newly mapped ports
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Regenerating Traffic Items for new port mapping...")
            traffic_items = ixNetwork.Traffic.TrafficItem.find()
            if len(traffic_items) > 0:
                for ti in traffic_items:
                    ixNetwork.info(f"Step {myStep.add_minor():.1f} - Generating Traffic Item: {ti.Name}")
                    try:
                        ti.Generate()
                    except Exception as e:
                        ixNetwork.warn(f"Warning generating {ti.Name}: {e}")
            else:
                ixNetwork.info(f"Step {myStep.add_minor():.1f} - No pre-existing Traffic Items found to regenerate.")

            # 3. Force global traffic to apply the newly generated profiles to the hardware
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Applying Global Traffic...")
            try:
                ixNetwork.Traffic.Apply()
            except Exception as e:
                ixNetwork.warn(f"Global traffic apply warning: {e}")

            # 4. Clear statistics right before the QuickTest takes over
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Clearing stale statistics...")
            ixNetwork.ClearStats()


            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Applying QuickTest Configuration...")
            qt.Apply()
            
            ixNetwork.info(f"Step {myStep.add_minor():.1f} - Starting QuickTest...")
            qt.Start()
            
            verify_quick_test_initialization(ixNetwork, qt, myStep)
            monitor_quick_test_progress(ixNetwork, qt, myStep, interval=15)
            
            ixNetwork.info(f"Step {myStep.add()} - Gathering results into {TestVars.results_dir}")
            download_linux_results(session, ixNetwork, qt, test_name, myStep)

        ixNetwork.info(f"Step {myStep.add()} - Testing Complete. Tearing down session.")
        session.Session.remove()
        del ixNetwork
        del session

    except Exception as e:
        print(f"\nCRITICAL ERROR: {traceback.format_exc()}")
        if 'session' in locals():
            session.Session.remove()

if __name__ == '__main__':
    main()