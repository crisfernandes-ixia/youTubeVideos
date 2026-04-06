#!/bin/bash

# -----------------------------------------------------------------------------
# CONFIGURATION VARIABLES
# -----------------------------------------------------------------------------
INGRESS_PORT="swp0"             # Port connected to Ixia Talker (Source)
EGRESS_PORT1="swp1"             # Egress Port for Policing Stream
EGRESS_PORT2="swp2"             # Egress Port for Gating Stream
EGRESS_PORT3="swp3"             # Egress Port for Filtering Stream

# Shared VLAN ID
SHARED_VID=100

# SCENARIO 1: POLICING STREAM (802.1Qci Flow Metering)
POLICE_MAC="00:12:02:00:00:01"
POLICE_VID=$SHARED_VID
POLICE_RATE="10Mbit"
BURST_SIZE="10k"

# SCENARIO 2: GATING STREAM (802.1Qci Stream Gating)
GATE_MAC="00:13:02:00:00:01"
GATE_VID=$SHARED_VID
OPEN_TIME="100000"              # 100us in nanoseconds
CLOSE_TIME="900000"             # 900us in nanoseconds
GATE_ID=1                       # Unique ID for the hardware gate entry

# SCENARIO 3: FILTERING STREAM (802.1Qci Stream Blocking/Dropping)
# IMPLEMENTED VIA EXTREME POLICING (Rate set to 1kbit to drop everything)
FILTER_MAC="00:14:02:00:00:01"  # Unique MAC for Filtering
FILTER_VID=$SHARED_VID
FILTER_POLICE_RATE="1kbit"      # Rate so low it causes a 100% drop (effective filtering)

echo "---------------------------------------------------------------------"
echo "Configuring 802.1Qci Demo (Policing, Gating, Filtering) on NXP LS1028A"
echo " ALL STREAMS ON VLAN $SHARED_VID"
echo " Policing Stream: MAC $POLICE_MAC (swp1)"
echo " Gating Stream:   MAC $GATE_MAC (swp2)"
echo " Filtering Stream:MAC $FILTER_MAC (swp3 - BLOCKED via Policing)"
echo "---------------------------------------------------------------------"

# 1. Clean up existing Qdiscs
echo "[1/6] Cleaning up existing configurations on $INGRESS_PORT..."
tc qdisc del dev $INGRESS_PORT clsact 2> /dev/null

# 2. Initialize the Classifier-Action (clsact) qdisc
echo "[2/6] Initializing clsact qdisc..."
tc qdisc add dev $INGRESS_PORT clsact

# 3. MANDATORY: Add Static FDB Entries for All Three Streams
echo "[3/6] Adding static FDB entries (MAC learning fix)..."
bridge fdb replace $POLICE_MAC dev $EGRESS_PORT1 vlan $POLICE_VID master static
bridge fdb replace $GATE_MAC dev $EGRESS_PORT2 vlan $GATE_VID master static
bridge fdb replace $FILTER_MAC dev $EGRESS_PORT3 vlan $FILTER_VID master static

# 4. Simplify Chain Setup to only jump to the final PSFP stage (Chain 30000)
# This reverts to the original working setup for Policing/Gating.
echo "[4/6] Configuring hardware offload chains to Chain 30000 (PSFP)..."
tc filter add dev $INGRESS_PORT ingress chain 0 pref 49152 flower skip_sw action goto chain 30000

# 5. Apply Qci Rules to Chain 30000
echo "[5/6] Applying 802.1Qci rules (All rules applied to the working Chain 30000)..."

# SCENARIO 3: FILTERING/BLOCKING RULE (Implemented as extreme Policing)
echo "  - Adding Filtering Rule: Unconditionally Drop on MAC $FILTER_MAC (Applied via $FILTER_POLICE_RATE limit)"
tc filter add dev $INGRESS_PORT ingress chain 30000 protocol 802.1Q flower skip_sw \
    dst_mac $FILTER_MAC vlan_id $FILTER_VID \
    action police rate $FILTER_POLICE_RATE burst 1b conform-exceed drop/ok

# SCENARIO 1: POLICING RULE (Flow Metering)
echo "  - Adding Policing Rule: $POLICE_RATE limit on MAC $POLICE_MAC"
tc filter add dev $INGRESS_PORT ingress chain 30000 protocol 802.1Q flower skip_sw \
    dst_mac $POLICE_MAC vlan_id $POLICE_VID \
    action police rate $POLICE_RATE burst $BURST_SIZE conform-exceed drop/ok

# SCENARIO 2: GATING RULE (Stream Gating)
echo "  - Adding Gating Rule (ID $GATE_ID): 100us Open / 900us Close on MAC $GATE_MAC"
tc filter add dev $INGRESS_PORT ingress chain 30000 protocol 802.1Q flower skip_sw \
    dst_mac $GATE_MAC vlan_id $GATE_VID \
    action gate base-time 0 sched-entry OPEN $OPEN_TIME $GATE_ID -1 \
    sched-entry CLOSE $CLOSE_TIME $GATE_ID -1


# 6. Verification
echo "[6/6] Verification:"
echo "---------------------------------------------------------------------"
echo "FDB Entries for Streams (All Ports):"
bridge fdb show | grep -E "$POLICE_MAC|$GATE_MAC|$FILTER_MAC"

echo ""
echo "Active Qci TC Filters on $INGRESS_PORT (Chain 30000):"
tc -s filter show dev $INGRESS_PORT ingress chain 30000
echo "---------------------------------------------------------------------"
root@ls1028ardb:~/qci#
