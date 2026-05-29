import random, time, math
import paramiko

def generate_mac_address():
    mac_address = [random.randint(0x00, 0xff) for _ in range(5)]
    mac_address.insert(0,170)
    return ':'.join('{:02x}'.format(byte) for byte in mac_address)

def floor_to_nearest_hundred(n):
    return math.floor(n / 100) * 100


class Step:
    def __init__(self):
        self.major = 0
        self.minor = 0

    def add(self):
        # Start a new major step and reset the minor step to 0
        self.major += 1
        self.minor = 0

        # Returning an integer ensures it prints cleanly as "1", "2", "3"
        return self.major

    def add_minor(self):
        # Increment the minor sub-step
        self.minor += 1

        # Combine them safely without floating-point precision errors
        return float(f"{self.major}.{self.minor}")


class MacAddressGenerator:
    def __init__(self):
        self.prefix = "00:a9:00:00:00:00"
        self.counter = 2  # Initialize the counter with 2

    def generate_mac_address(self):
        mac_address = f"{self.prefix[:-5]}{self.counter:02X}:{self.counter:02X}"
        self.counter += 1
        if self.counter > 255:
            raise StopIteration("No more unique MAC addresses available")
        return mac_address

    def __iter__(self):
        return self

    def __next__(self):
        return self.generate_mac_address()

def is_reserved_mac(mac_address) -> bool:
    reserved_prefixes = ['01:00:5e', '33:33', '00:00:00', '01:08:C2', '00:01:FF', '00:02:FF']
    for prefix in reserved_prefixes:
        if mac_address.startswith(prefix):
            return True
    return False

def generate_unique_mac_list(num_addresses):
    mac_list = set()
    while len(mac_list) < num_addresses:
        mac_address = generate_mac_address()
        if not is_reserved_mac(mac_address):
            mac_list.add(mac_address)
    return list(mac_list)

class testVars: pass

def expand_time_abbreviation(abbreviation) -> str :
    abbreviations = {
        'ms' : 'milliseconds',
        'msec' : 'milliseconds',
        'sec': 'seconds',
        's': 'seconds',
        'ns' : 'nanoseconds',
        'nsec' : 'nanoseconds',
        'us' : 'microseconds'
    }
    return abbreviations.get(abbreviation, 'Unknown abbreviation')

def convert_to_nanoseconds(value : str, unit : int) -> int:
    units = {
        'ns': 1,
        'nsec' : 1,
        'us': 1000,
        'ms': 1000 * 1000,
        'msec' : 1000 * 1000,
        'sec': 1000 * 1000 * 1000,
        's': 1000 * 1000 * 1000,
        'min': 1000 * 1000 * 1000 * 60,
        'hr': 1000 * 1000 * 1000 * 60 * 60,
        'day': 1000 * 1000 * 1000 * 60 * 60 * 24
    }

    if unit in units:
        conversion_factor = units[unit]
        nanoseconds = value * conversion_factor
        return nanoseconds
    else:
        return "Invalid unit of time."
    
def _myRun(ixNet,logStatus : bool = True):
        preventInfLoop = 30        
        ixNet.Traffic.Start()        
        trafficNotRunnning = True
        while trafficNotRunnning: 
            currentTrafficState = ixNet.Traffic.State
            if logStatus:
                ixNet.info('Currently traffic is in ' + currentTrafficState + ' state')
            if currentTrafficState == 'started': 
                trafficNotRunnning = False
            time.sleep(2)
            preventInfLoop -= 2
            if preventInfLoop < 1: 
                return False
        return True

def checkTrafficState(ixNet, state, logStatus : bool = True):
        pleaseWait = True
        preventInfLoop = 60
        while pleaseWait: 
            currentTrafficState = ixNet.Traffic.State
            if logStatus:
                ixNet.info('Currently traffic is in ' + currentTrafficState + ' state')
            if currentTrafficState == state: 
                pleaseWait = False
            else:
                time.sleep(2)
            
            preventInfLoop -= 2
            if preventInfLoop < 1: 
                return False
        return True

def compare_numbers(num1, num2, thresholdNum = 0.99):
    threshold = thresholdNum
    difference = abs(num1 - num2)
    avg = (num1 + num2) / 2
    percent_difference = difference / avg
    
    if percent_difference <= (1 - threshold):
        return True
    else:
        return False
    
def getPktsPerSecond(packet_size_in_bytes : int = 100, preamble_size : int = 8, intergap_size : int = 12, transmission_rate_in_Mbps : int = 10_000):
    bps_per_second = transmission_rate_in_Mbps * 1_000_000
    frameSize = packet_size_in_bytes + preamble_size + intergap_size
    frameSizeInBits = frameSize * 8 
    packets_per_second = bps_per_second / frameSizeInBits
    print("Packets per second:", packets_per_second)
    return packets_per_second

def getPktsPerDuration(packet_size_in_bytes : int = 100, preamble_size : int = 8, intergap_size : int = 12, total_time_in_us : int = 300, transmission_rate_in_Mbps : int = 10_000):
    pktPerSec = getPktsPerSecond(packet_size_in_bytes, preamble_size, intergap_size, transmission_rate_in_Mbps)
    return  math.floor( (pktPerSec * total_time_in_us) / 1_000_000)
        
def find_key_with_word(dictionary, word):
    for key in dictionary:
        if word in key:
            return key
    return None

def getNanoSeconds(dateVal:str):
    date_components = dateVal.split()
    time_with_fractional_seconds = date_components[1]
    seconds_part = time_with_fractional_seconds.split(':')[2]
    seconds, nanoseconds = seconds_part.split('.')
    total_nanoseconds = int(seconds) * 10**9 + int(nanoseconds)
    return total_nanoseconds

def dut_connect(ip,username,password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=username, password=password)
    return client

def reboot_and_wait(ip,username,password):
    print("Rebooting the nxp switch aka DUT...")
    client = dut_connect(ip,username,password)
    client.exec_command("reboot")
    client.close()

    time.sleep(10)

    while True:
        try:
            print("Trying to reconnect...")
            client = dut_connect(ip,username,password)
            print("Server is back online.")
            return client 
        except Exception as e:
            print(f"Failed to connect: {e}")
            time.sleep(5)

def generate_taprio_script(interface, schedule, base_time=0):
    """
    Dynamically generates the tc qdisc taprio script based on the Python schedule.
    """
    lines = [
        "#!/bin/bash",
        f"echo 'Applying dynamic Qbv configuration for {interface}'",
        f"tc qdisc replace dev {interface} parent root handle 100 taprio \\",
        "    num_tc 8 queues 1@0 1@1 1@2 1@3 1@4 1@5 1@6 1@7 \\",
        "    map 0 1 2 3 4 5 6 7 \\",
        f"    base-time {base_time} \\"
    ]

    for entry in schedule:
        mask = sum(1 << p for p in entry['priorities'])
        hex_mask = f"{mask:02X}"
        # We unconditionally add the backslash here so it connects to 'flags 2'
        line = f"    sched-entry S {hex_mask} {entry['duration_ns']} \\"
        lines.append(line)

    lines.append("    flags 2")
    lines.append(f"tc qdisc show dev {interface}")
    
    return "\n".join(lines)


def apply_dynamic_dut_config(ip, username, password, taprio_script):
    """
    Connects to the DUT, starts gPTP, and applies the dynamic Taprio configuration.
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to DUT at {ip}...")
        client.connect(ip, username=username, password=password)
        
        print("Starting gPTP (fgptp.sh start)...")
        client.exec_command("fgptp.sh start")
        time.sleep(5) # Allow AS daemon to initialize
        
        print("Pushing dynamic Taprio script to DUT...")
        command = f"cat << 'EOF' > /tmp/dynamic_qbv.sh\n{taprio_script}\nEOF\nchmod +x /tmp/dynamic_qbv.sh\n/tmp/dynamic_qbv.sh"
        stdin, stdout, stderr = client.exec_command(command)
        
        output = stdout.read().decode()
        errors = stderr.read().decode()
        
        print(output)
        if errors:
            print(f"DUT Configuration Errors: {errors}")
            
    except Exception as e:
        print(f"Failed to configure DUT: {e}")
    finally:
        client.close()