# Basic imports for Ryu
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6

class SDNApplication(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super(SDNApplication, self).__init__(*args, **kwargs)

    def info(self, text):
        print("*"*20)
        print("* %s" % text)
        print("*"*20)

    # Set a flow on a switch
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

    # New switch
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    # Make sure the name of the function does not collide with those
    # of classes, that inherit from SDNApplication. Otherwise this
    # function will not be invoked.
    def __sdn_app_switch_features_handler(self, ev):
        msg      = ev.msg
        datapath = msg.datapath

        print("switch with id {:d} connected".format(datapath.id))

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
