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

class CockpitApp(app_manager.RyuApp):

    def __init__(self, *args, **kwargs):
        super(CockpitApp, self).__init__(*args, **kwargs)

    def info(self, text):
        print("*" * (len(text) + 4))
        print("* {:s} *".format(text))
        print("*" * (len(text) + 4))

    def program_flow(self, dp, match, actions, priority = 0,
        hard_timeout = 600, idle_timeout = 60
    ):
        """ Programs a new flow into a switch.

            Programming a new flow with the exact same match of an
            existing one will replace the existing flow.
        """
        flowmod = parser.OFPFlowMod(
            dp,
            match = match,
            instructions = [
                parser.OFPInstructionActions(
                    ofproto.OFPIT_APPLY_ACTIONS,
                    actions
                )
            ],
            priority = priority,
            hard_timeout = hard_timeout,
            idle_timeout = idle_timeout
        )

        dp.send_msg(flowmod)

    def send_pkt(self, dp, data, port = ofproto.OFPP_FLOOD):
        """ Convenience method that instructs a switch to forward
            a packet from the controller.
        """
        out = parser.OFPPacketOut(
            datapath = dp,
            actions = [parser.OFPActionOutput(port)],
            in_port = dp.ofproto.OFPP_CONTROLLER,
            data = data,
            buffer_id = ofproto.OFP_NO_BUFFER
        )

        dp.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    # Make sure the name of the function does not collide with those
    # of classes, that inherit from this class. Otherwise this
    # function will not be invoked.
    def __cockpit_app_switch_features_handler(self, ev):
        dp = ev.msg.datapath

        print("switch with id {:d} connected".format(dp.id))

        # Install default flow
        # I.e., forward all unmatched packets to controller
        self.program_flow(
            dp,
            parser.OFPMatch(), # match all packets
            [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)],
            hard_timeout = 0, # no timeout
            idle_timeout = 0  # no timeout
        )

        # Prevent switches from truncating packets when forwarding
        # to controller
        dp.send_msg(dp.ofproto_parser.OFPSetConfig(
            dp,
            dp.ofproto.OFPC_FRAG_NORMAL,
            0xffff
        ))
