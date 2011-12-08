#!/bin/sh
#
# Firewall for house server.
#
# 'FOR NOW' is appended to comments wherever the rules are temporary
#
# TODO:
# * Make LOCAL_BROADCAST dynamic.
# * Possibly add IF0 to rules.
#
# Add the following to /etc/sysctl.conf for more security:
# net.ipv4.conf.all.rp_filter = 1
# net.ipv4.tcp_timestamps = 0
# net.ipv4.conf.all.accept_source_route = 0
# net.ipv4.icmp_echo_ignore_broadcasts = 1
# net.ipv4.icmp_ignore_bogus_error_responses = 1

check() {
	if [ ! -x "$1" ] ; then
		echo "$1 not found or is not executable"
		exit 1
	fi
}


# Variable definitions.
IPT="/sbin/iptables"
check $IPT

IF0="eth0"
LO="lo"

UNIVERSE="0.0.0.0/0"
MULTICAST="224.0.0.0/24"
BROADCAST="255.255.255.255"
LOCAL_BROADCAST="128.32.112.255"

# Service ports.
SSH_PORT=22
LDAP_PORT=389
IMAP_PORT=143
IMAPS_PORT=993
SMTP_PORT=25
SMTP_FORWARD_PORT=465
HTTP_PORT=80
HTTPS_PORT=443
HTTP_AUTH_PORT=4444
BOOTPC_PORT=68
NTP_PORT=123
RSYNC_PORT=873
IRC_PORT=6697
QWEBIRC_PORT=9090

# Flush old rules.
$IPT -F
$IPT -t mangle -F
$IPT -t nat -F
$IPT -X


# Set defaults to deny.
$IPT -P INPUT DROP
$IPT -P OUTPUT DROP
$IPT -P FORWARD DROP


# ===== "log-and-drop" chain =====
# Logs all packets before dropping.
$IPT -N log-and-drop
$IPT -A log-and-drop -j LOG --log-level info --log-prefix "iptables: "
$IPT -A log-and-drop -j DROP


# ===== "icmp-chain" chain =====
# Allow ICMP packets in general.
$IPT -N icmp-chain
$IPT -A icmp-chain -p icmp --icmp-type 0 -j ACCEPT
$IPT -A icmp-chain -p icmp --icmp-type 3 -j ACCEPT
$IPT -A icmp-chain -p icmp --icmp-type 8 \
-m limit --limit 5/s --limit-burst 5 -j ACCEPT
$IPT -A icmp-chain -p icmp --icmp-type 11 -j ACCEPT
$IPT -A icmp-chain -j log-and-drop


# ===== "common-attacks" chain =====
# Chain that checks for common attacks.
$IPT -N common-attacks

# Make sure new incoming TCP connections are SYN packets.
$IPT -A common-attacks -p tcp ! --syn -m state --state NEW -j log-and-drop

# Check for packets with incoming fragments.
$IPT -A common-attacks -f -j log-and-drop

# Check for malformed XMAS packets.
$IPT -A common-attacks -p tcp --tcp-flags ALL ALL -j log-and-drop

# Check for malformed NULL packets.
$IPT -A common-attacks -p tcp --tcp-flags ALL NONE -j log-and-drop


# ===== "services" chain =====
# Allow certain services
$IPT -N services

# Allow 3 ssh attempts per IP address per minute.
$IPT -A services -p tcp --dport $SSH_PORT \
-m recent --update --seconds 60 --hitcount 3 -j log-and-drop
$IPT -A services -p tcp --dport $SSH_PORT \
-m recent --set -j ACCEPT

# Allow ldap.
$IPT -A services -p tcp --dport $LDAP_PORT -j ACCEPT
# Allow imap.
$IPT -A services -p tcp --dport $IMAP_PORT -j ACCEPT
# Allow imaps.
$IPT -A services -p tcp --dport $IMAPS_PORT -j ACCEPT

# Allow smtp.
$IPT -A services -p tcp --dport $SMTP_PORT -j ACCEPT

# Alow http.
$IPT -A services -p tcp --dport $HTTP_PORT -j ACCEPT

# Allow https.
$IPT -A services -p tcp --dport $HTTPS_PORT -j ACCEPT

# Allow authentication for http on hkn website.
$IPT -A services -p tcp --dport $HTTP_AUTH_PORT -j ACCEPT

# Allow bootpc.
$IPT -A services -p udp --dport $BOOTPC_PORT -j ACCEPT

# Allow ntp.
$IPT -A services -p udp --dport $NTP_PORT -j ACCEPT

# Allow rsync
$IPT -A services -p tcp --dport $RSYNC_PORT -j ACCEPT

# Allow IRC
$IPT -A services -p tcp --dport $IRC_PORT -j ACCEPT

# Allow qwebirc
$IPT -A services -p tcp --dport $QWEBIRC_PORT -j ACCEPT

# Log and drop everything else.
$IPT -A services -j log-and-drop


# Allow all on loopback.
$IPT -A INPUT -i $LO -s 127.0.0.1 -j ACCEPT
$IPT -A OUTPUT -o $LO -d 127.0.0.1 -j ACCEPT


#
# ***** INPUT chain ******
#

# Enable icmp-chain.
$IPT -A INPUT -p icmp -j icmp-chain

# Check for common attacks
$IPT -A INPUT -j common-attacks

# Allow established connections.
$IPT -A INPUT -m state --state ESTABLISHED -j ACCEPT

# Don't log and just drop all multicast traffic.
$IPT -A INPUT -d $MULTICAST -j DROP

# Don't log and just drop all broadcast traffic.
$IPT -A INPUT -d $LOCAL_BROADCAST -j DROP
$IPT -A INPUT -d $BROADCAST -j DROP

# Eanble services chain.
$IPT -A INPUT -m state --state NEW -j services

# Log and drop everything else.
$IPT -A INPUT -j log-and-drop


#
# ***** OUTPUT chain *****
#

# Allow new/established/related outgoing connections.
$IPT -A OUTPUT -m state --state NEW,ESTABLISHED,RELATED -j ACCEPT

# Log and drop everything else.
$IPT -A OUTPUT -j log-and-drop


#
# ***** FORWARD chain *****
#

# Listen on another port to forward to 25. This is because lots of ISP's block
# outgoing messages to port 25.

$IPT -t nat -A PREROUTING -p tcp --dport $SMTP_FORWARD_PORT -j REDIRECT \
--to-ports $SMTP_PORT

# Log and drop everything FOR NOW.
$IPT -A FORWARD -j log-and-drop
