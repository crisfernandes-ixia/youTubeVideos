from scapy.all import rdpcap, wrpcap
import os


def print_gate_counters(gate_stats):
    print("Gate statistics:")
    for gate_num in sorted(gate_stats.keys()):
        stats = gate_stats[gate_num]
        print(f"Gate {gate_num}:")
        print(f"  Valid count  : {stats['valid_count']}")
        print(f"  Invalid count: {stats['invalid_count']}\n")

def check_packet_in_gate_window(first_packet_time_ns, packet_time_ns, gate_start_ns, gate_end_ns, cycle_time_ns, pkt_num):
    # Calculate difference ignoring complete cycles by mod cycle time
    diff_ns = (packet_time_ns - first_packet_time_ns) % cycle_time_ns

    # Check if packet falls within gate open window [gate_start_ns, gate_end_ns)
    if gate_start_ns <= diff_ns < gate_end_ns:
        return True
    else:
        print(f"Pkt: {pkt_num} - Gate Start/End: {gate_start_ns} {gate_end_ns}  Pkt_time: {packet_time_ns} diff: {diff_ns}")
        return False

def generate_gate_windows_ns(gate_config):
    gate_windows_ns = {}
    start_ns = 0
    for gate_num in sorted(gate_config.keys()):
        duration_ns = gate_config[gate_num]['time_us'] * 1000  # Convert microseconds to nanoseconds
        gate_windows_ns[gate_num] = {
            'start_ns': start_ns if start_ns == 0 else start_ns + 1,
            'end_ns': start_ns + duration_ns
        }
        gate_windows_ns[gate_num]['valid_count'] = 0
        gate_windows_ns[gate_num]['invalid_count'] = 0

        start_ns += duration_ns
    return gate_windows_ns

def main():

    total_pkt_count = 0
    first_packet = None
    cycle_start_ts_ns = None

    downloads_path = os.path.expanduser('~/Downloads')
    pcap_file = os.path.join(downloads_path, 'input.pcapng')  # Change to your input file

    # Gate config: gate time in microseconds, and VLAN priorities allowed
    gate_config = {
        1: {'time_us': 250, 'priorities': [0, 1, 2, 3]},
        2: {'time_us': 250, 'priorities': [4]},
        3: {'time_us': 250, 'priorities': [5]},
        4: {'time_us': 250, 'priorities': [6, 7]},
    }

    priority_to_gate_dict = {}
    for gate_num, gate in gate_config.items():
        for pri in gate['priorities']:
            priority_to_gate_dict[pri] = gate_num
    priority_to_times = generate_gate_windows_ns(gate_config)

    # Calculate cycle time in microseconds
    cycle_time_ns = (sum(gate['time_us'] for gate in gate_config.values())) * 1000

    packets = rdpcap(pcap_file)
    for pkt in packets:
        total_pkt_count += 1
        if pkt.haslayer('Dot1Q'):
            prio = pkt['Dot1Q'].prio
            packet_ns = int(pkt.time * 1e9)
            if first_packet is None:
                first_packet_ns = int(pkt.time * 1e9)
                cycle_start_ts_ns = (first_packet_ns // cycle_time_ns) * cycle_time_ns
            exp_gate = priority_to_gate_dict[prio]
            result = check_packet_in_gate_window(
                cycle_start_ts_ns,
                packet_ns,
                priority_to_times[exp_gate]['start_ns'],
                priority_to_times[exp_gate]['end_ns'],
                cycle_time_ns, total_pkt_count)
            if result:
                priority_to_times[exp_gate]['valid_count'] += 1
            else:
                print(f"Invalid packet number: {total_pkt_count}")
                priority_to_times[exp_gate]['invalid_count'] += 1
        else:
            continue

    print(f"\n **** Total Number of packets in pcap file: {total_pkt_count}\n")
    print_gate_counters(priority_to_times)

if __name__ == '__main__':
    main()


