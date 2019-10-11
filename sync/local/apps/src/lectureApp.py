# This is a wrapper file for the apps that are located in the
# myapps folder. The file is changed automatically (see script_run_watch.py)
# so do not change anything here unless you know what you are doing!
# The tm task line and the USE_APP line below are overwritten every time 
# a .py file in the myapps folder is changed.

# --------------------<DO NOT CHANGE THIS>

#tm task=demoAlumni

USE_APP = '/vagrant_data/myapps/demo.py'

# --------------------</DO NOT CHANGE THIS>

# Basic imports for Ryu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6, icmp

from netaddr import IPAddress, IPNetwork

import sys, imp # required to import the app

MATCHES = dict(
    IP_SRC = 'ipv4_src',
    IP_DST = 'ipv4_dst',
    MAC_SRC = 'eth_src',
    MAC_DST = 'eth_dst'
)



class Switch():

    def __init__(self, wrapper, datapath):
        self.wrapper = wrapper # points to the wrapper (not the app in the myapps folder!)
        self.datapath = datapath # datapath object to communicate with the switch
        self.id = datapath.id
        
    def flood(self, pkt):
        self.wrapper.send_pkt(self.datapath, pkt.data, port = ofproto.OFPP_FLOOD)

    def send_packet(self, pkt, port):
        self.wrapper.send_pkt(self.datapath, pkt.data, port = port)
           
    def install_rule(self, **kwargs):

        ofproto = self.datapath.ofproto

        match = parser.OFPMatch(**kwargs.get('match'))

        action = parser.OFPActionOutput(kwargs.get('action').get('output'))


        self.wrapper.set_flow(self.datapath, match, [action], priority = priority)

    def execute_rule(self, rule):
        print ">> install new rule in switch %d: match=%s, action=%s" % (
            self.id, str(rule.matches), str(rule.actions))

        actions = []
        #action = parser.OFPActionOutput(kwargs.get('action').get('output'))

        match_dict = {}
        for k,v in rule.matches.iteritems():
            if k == '*':
                match_dict = {}
                break   
            if k in MATCHES:
                match_dict[MATCHES[k]] = v
        
        # add eth_type match in case of ip
        if 'IP_DST' in rule.matches or 'IP_SRC' in rule.matches:
            match_dict['eth_type'] = ether_types.ETH_TYPE_IP

        for k, v in rule.actions.iteritems():
            if k == 'OUTPUT':
                # output flood
                if v == 'flood' or v == 'FLOOD':
                    actions.append(parser.OFPActionOutput(ofproto.OFPP_FLOOD))
                # output to a specific port
                if isinstance(v, int):
                    actions.append(parser.OFPActionOutput(v))
            if k == 'DROP':
                actions = []
                break
            if k == 'CONTROLLER':
                actions.append(parser.OFPActionOutput(ofproto.OFPP_CONTROLLER))


        match = parser.OFPMatch(**match_dict)

        self.wrapper.set_flow(self.datapath, match, actions, priority = rule.prio)


class Packet():

    def __init__(self, data):
        # generic
        self.type = 'unknown'
        # checker
        self.is_arp = False
        self.is_ip = False
        self.is_ipv4 = False
        self.is_ipv6 = False
        self.is_icmp = False
        self.is_tcp = False
        self.is_udp = False
        # addresses
        self.ip_src = None
        self.ip_dst = None
        self.ipv6_src = None
        self.ipv6_dst = None
        self.mac_src = None
        self.mac_dst = None

        self.data = data
        pkt = packet.Packet(data)
        self.pkt = pkt

        # ethernet
        eth = pkt.get_protocol(ethernet.ethernet)
        self.mac_src = eth.src
        self.mac_dst = eth.dst
        self.eth = eth
        self.type = 'eth (%x)' % eth.ethertype

        # arp
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            _arp = pkt.get_protocol(arp.arp)
            self.is_arp = True
            self.type = 'arp (%x)' % eth.ethertype
            self.arp_ip_src = _arp.src_ip
            self.arp_ip_dst = _arp.dst_ip
            self.arp_mac_src = _arp.src_mac
            self.arp_mac_dst = _arp.dst_mac
            self.arp_opcode = _arp.opcode

        # ipv4
        ip = pkt.get_protocol(ipv4.ipv4)
        if ip is not None:
            self.is_ip = True
            self.is_ipv4 = True
            self.type = 'ipv4 (%x)' % (eth.ethertype)
            self.ip_src = ip.src
            self.ip_dst = ip.dst

            # icmp
            _icmp = pkt.get_protocol(icmp.icmp)
            if _icmp is not None:
                self.is_icmp = True
                #print(dir(_icmp))
                self.icmp_type = _icmp.type # ICMP type
                self.icmp_code = _icmp.code # ICMP subtype

        # ipv6
        _ipv6 = pkt.get_protocol(ipv6.ipv6)
        if _ipv6 is not None:
            self.is_ipv6 = True
            self.type = 'ipv6 (%x)' % (eth.ethertype)
            self.ipv6_src = _ipv6.src
            self.ipv6_dst = _ipv6.dst
            
        # to be consistent with lecture
        self.IP_SRC = self.ip_src
        self.IP_DST = self.ip_dst
        self.MAC_SRC = self.mac_src
        self.MAC_DST = self.mac_dst
        self.IPV6_SRC = self.ipv6_src
        self.IPV6_DST = self.ipv6_dst

    def __str__(self):
        if self.is_arp:
            if self.arp_opcode == 1:
                return "type=%s [ARP request] mac_src=%s mac_dst=%s  who has %s?" % (
                    self.type, self.mac_src, self.mac_dst, self.arp_ip_dst)
            if self.arp_opcode == 2:
                return "type=%s [ARP reply] mac_src=%s mac_dst=%s  I do! (%s)" % (
                    self.type, self.mac_src, self.mac_dst, self.arp_mac_src) 
                return "type=%s [ARP opcode=%d] mac_src=%s mac_dst=%s  who has %s?" % (
                    self.type,  self.arp_opcode, self.mac_src, self.mac_dst)  
        if self.is_icmp:
            if self.icmp_type == 8 and self.icmp_code == 0:
                return "type=%s [ICMP request] ip_src=%s ip_dst=%s" % (
                    self.type, self.ip_src, self.ip_dst)
            if self.icmp_type == 0 and self.icmp_code == 0:
                return "type=%s [ICMP reply] ip_src=%s ip_dst=%s" % (
                    self.type, self.ip_src, self.ip_dst)  
            if self.icmp_type == 3:
                return "type=%s [ICMP destination unreachable] ip_src=%s ip_dst=%s" % (
                    self.type, self.ip_src, self.ip_dst) 
            if self.icmp_type == 9:
                return "type=%s [ICMP router advertisement] ip_src=%s ip_dst=%s" % (
                    self.type, self.ip_src, self.ip_dst) 
            if self.icmp_type == 10:
                return "type=%s [ICMP router solicitation] ip_src=%s ip_dst=%s" % (
                    self.type, self.ip_src, self.ip_dst)         
            return "type=%s [ICMP type=%d code=%d] ip_src=%s ip_dst=%s" % (
                self.type, self.ip_src, self.ip_dst, self.icmp_type, self.icmp_code)                  
        if self.is_ipv4:
            return "type=%s ip_src=%s ip_dst=%s" % (self.type, self.ip_src, self.ip_dst)
        if self.is_ipv6:
            return "type=%s ip_src=%s ip_dst=%s" % (self.type, self.ipv6_src, self.ipv6_dst)

        return "type=%s mac_src=%s mac_dst=%s" % (self.type, self.mac_src, self.mac_dst)

    def __repr__(self):
        return self.__str__()


class LectureApp(app_manager.RyuApp):
    """ Helper ryu app that will load an app from the myapps folder """
    def __init__(self, *args, **kwargs):
        super(LectureApp, self).__init__(*args, **kwargs)
        try:
            # the app needs access to some imports
            sys.path.insert(0,'/vagrant_data/myapps') 
            # now load the app
            app = imp.load_source('app', USE_APP)
            self.app = app.Application()
        except IOError as e:
            self.info("Error: app not found (path=%s) --> exit now" % USE_APP)
            exit(1)
        except AttributeError as e:
            self.info("Error: app files need an Application class, not found --> exit now")
            exit(1)

        self.switches = dict() # store switches by datapath id

        # The total_packets variable keeps track of the
        # number of packets that have been forwarded to the
        # controller.
        self.total_packets = 0

    def info(self, text):
        print "*"*20
        print "* %s" % text
        print "*"*20


    # Install a flow rule into the switch
    def set_flow(self, datapath, match, actions, priority=0, hard_timeout=600, idle_timeout=60):
        inst    = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        flowmod = parser.OFPFlowMod(datapath, 
            match=match,
            instructions=inst,
            priority=priority,
            hard_timeout=hard_timeout,
            idle_timeout=idle_timeout)
        datapath.send_msg(flowmod)

    # Send a packet out of a switch
    def send_pkt(self, datapath, data, port=ofproto.OFPP_FLOOD):
        actions = [parser.OFPActionOutput(port)]
        out     = parser.OFPPacketOut(
            datapath=datapath, 
            actions=actions,
            in_port=datapath.ofproto.OFPP_CONTROLLER,
            data=data,
            buffer_id=ofproto.OFP_NO_BUFFER)
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg      = ev.msg
        datapath = msg.datapath

        # create a new switch object for the app to work with
        switch = Switch(self, datapath)

        self.switches[datapath.id] = switch

        self.app.on_connect(switch)

        # install the default-to-controller-flow
        self.set_flow(datapath, 
            parser.OFPMatch(), # match on every packet
            [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)], # action is sent_to_controller
            hard_timeout=0, # never delete this flow
            idle_timeout=0 # never delete this flow
        )

        # Prevent truncation of packets
        datapath.send_msg(
            datapath.ofproto_parser.OFPSetConfig(
                datapath,
                datapath.ofproto.OFPC_FRAG_NORMAL,
                0xffff
            )
        )


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """ This method is invoked when a packet does not match any
            of the rules deployed on a switch. The controller can
            take subsequent action to update the switch flowtable entries
            and handle the packet itself.
        """      
        self.total_packets += 1 
        msg = ev.msg
        datapath = msg.datapath
        data = msg.data
        ofproto = datapath.ofproto
        in_port = msg.match["in_port"]

        pkt = packet.Packet(data)

        if datapath.id in self.switches:
            self.app.on_packet_in(Packet(data), self.switches[datapath.id], in_port)
        else:
            # should not happen
            switch = Switch(self, datapath)
            self.on_packet_in(Packet(data), switch, in_port)

    # not used atm
    def protect_our_network(self, datapath, in_port, src_ip, dst_ip):
        """ Count IP source addresses and launch contermeasures
            to protect the controller and prevent it from being flooded
            with packet_in messages.
        """
        if not self.packets_by_ip.has_key(src_ip):
            self.packets_by_ip[src_ip] = 0

        self.packets_by_ip[src_ip] += 1

        if in_port != 1:
            if self.packets_by_ip[src_ip] == 1000:
                # O.K., we've been playing nice long enough ...
                self.launch_countermeasures(datapath, src_ip)
                return True

            if self.packets_by_ip[src_ip] > 1000:
                # Just some lingering packets that got through before
                # our block rule became effective.
                return True

        # We dont want to talk to spammers.
        if in_port == 1 and self.packets_by_ip.get(dst_ip, 0) > 1000:
            return True

        return False

    # not used atm
    def launch_countermeasures(self, datapath, src_ip):
        """ Deploy a block rule based on IP source addresses """
        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_IP,
            ipv4_src = src_ip
        )

        # An empty action list indicates a drop rule
        self.set_flow(datapath, match, [], priority = 2)

        warn  = "   WARNING! Traffic limit exceeded for IP {:s}!".format(src_ip)
        warn += " Dropping packets!"
        print(warn)

    # not used atm
    def handle_arp(self, datapath, in_port, eth, data):
        """ This method implements a simple mechanism to install
            forwarding rules for ARP packets. Packets that are
            not handled by any of these rules are flooded to
            nearby switches.
        """
        ofproto = datapath.ofproto

        dst = eth.dst
        src = eth.src

        match = parser.OFPMatch(
            eth_type = ether_types.ETH_TYPE_ARP,
            eth_dst = src
        )

        # Progamm a flow that forwards ARP packets to directly connected
        # network nodes so we don't have to bother with subsequent
        # ARP packets anymore.
        self.set_flow(datapath, match, [parser.OFPActionOutput(in_port)],
            priority = 1)

        # Flood the received ARP message on all ports of the switch
        self.send_pkt(datapath, data, port = ofproto.OFPP_FLOOD)
