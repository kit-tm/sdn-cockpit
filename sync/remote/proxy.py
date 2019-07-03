import Pyro4
import requests
import json
import time
import select
import os
import subprocess
import shutil
import threading
import sys
import yaml
import pprint
import random
import psutil

from ipaddr import IPv4Address, IPv4Network
from termcolor import colored
from monitor import Monitor, BpfBuilder

def panic(*msg):
    print ""
    print "    " + colored("*"*20+" ERROR "+"*"*20, "white", "on_red")
    for m in msg:
        print "    " + m
    print "    " + colored("*"*47, "white", "on_red")
    exit(1)


def info(*msg):
    print ""
    print "    " + colored("*"*30, "white", "on_yellow")
    for m in msg:
        print "    " + m
    print "    " + colored("*"*30, "white", "on_yellow")

TASK_FILE = None

if len(sys.argv) > 1:
    SCENARIO_FILE = sys.argv[1]

    if "None.yaml" in SCENARIO_FILE:
        info("This task does not use the traffic generator.")
        print ""
        print "    Use the Mininet console (right screen, second window from the top)"
        print "    to create your own traffic. Use the help command to display "
        print "    the commands that are provided by Mininet."
        while True:
            time.sleep(10) # don't return

    if SCENARIO_FILE == "BootDummy":
        info("There is currently no traffic scenario selected.")
        print ""
        print "    Select a taffic scenario (or create a new one) and add the"
        print "    [#tm scenario=xxx] makro to start the scenario. Please contact your"
        print "    supervisor if there are any problems!"
        while True:
            time.sleep(10) # don't return

    if len(sys.argv) == 3:
        TASK_FILE = sys.argv[2]

else:
    SCENARIO_FILE = "/vagrant_data/local/apps/scenarios/simple1.yaml"

TRAFFIC_PROFILE = "default" # the traffic profile to be used
PROFILES = dict() # store initiated profiles


class Network(object):

    @staticmethod
    def from_dict(d):
        return Network(
            d.get("name"),
            d.get("alias", None),
            d.get("packet_ratio", 1.0),
            d.get("send_from_src", None),
            d.get("send_to_dst", None),
            d.get("recv_from_src", None),
            d.get("recv_to_dst", None),
            d.get("reject_from_src", None)
        )

    def __init__(self, name, alias = None, packet_ratio = 1.0, send_from_src = None, send_to_dst = None, recv_from_src = None, recv_to_dst = None, reject_from_src = None):
        self.name = name
        self.alias = alias if alias else ''
        self.packet_ratio = packet_ratio
        self.send_from_src = [] if not send_from_src else send_from_src
        self.send_to_dst = [] if not send_to_dst else send_to_dst
        self.recv_from_src = [] if not recv_from_src else recv_from_src
        self.recv_to_dst = [] if not recv_to_dst else recv_to_dst
        self.reject_from_src = [] if not reject_from_src else reject_from_src


class NetworkOracle(object):
    """docstring for NetworkOracle"""

    def __init__(self, scenario_file):
        super(NetworkOracle, self).__init__()
        self.scenario_file = scenario_file
        self.data = None
        self.ip_to_host = dict() # cache ip to host mapping
        self.networks = dict()
        self.senders = []
        self.src_ip2dst_host = dict()
        self.dst_ip2dst_host = dict()

        if not os.path.exists(scenario_file):
            panic(
                "Scenario file not found: %s" % scenario_file,
                "Make sure to specify an existing scenario!")

        with open(scenario_file, "r") as file:
            data = file.read()
            self.data = yaml.safe_load(data).get("root")

        if not self.data:
            raise Exception("Scenario file is not initialized")

        self.__init_networks()

    def __init_networks(self):
        for entry in self.data.get("networks"):
            net = Network.from_dict(entry)

            if net.send_from_src and net.send_to_dst:
                self.senders.append(net.name)

            for ip in net.recv_from_src:
                self.src_ip2dst_host[IPv4Network(ip)] = net

            for ip in net.recv_to_dst:
                self.dst_ip2dst_host[IPv4Network(ip)] = net

            self.networks.update({net.name : net})

    def get_traffic_profiles(self):
        return self.data.get("traffic_profiles", [])

    def get_used_profiles(self):
        return self.data.get("traffic").get("use_profiles", [])

    def get_cwd(self):
        cwd = self.data.get("working_directory")
        return os.path.join(os.getcwd(), cwd)

    def get_host(self, ip):
        return self.ip_to_host.get(ip)

    def learn_ip(self, ip, hostname):
        """ learn mapping between host and ip """
        self.ip_to_host[str(ip)] = hostname

    def get_hosts(self):
        return [_.get("name") for _ in self.data.get("topology").get("hosts")]

    def get_networks(self):
        return self.networks

    def get_network(self, name):
        return self.networks.get(name)

    def get_senders(self):
        return self.senders

    def _ip_in_subnets(self, ip, subnets):
        for s in subnets:
            if ip in IPv4Network(s):
                return True

        return False

    # deprecated
    def get_expected_destination(self, src_ip, dst_ip):
        src_ip = IPv4Address(src_ip)
        dst_ip = IPv4Address(dst_ip)

        # check constraints in order of precedence
        for net in self.networks.values():
            if self._ip_in_subnets(src_ip, net.reject_from_src):
                continue

            if self._ip_in_subnets(src_ip, net.recv_from_src):
                return net.name

            if self._ip_in_subnets(dst_ip, net.recv_to_dst):
                return net.name

        return None

    def get_expected_destinations(self, src_ip, dst_ip):
        src_ip = IPv4Address(src_ip)
        dst_ip = IPv4Address(dst_ip)

        dst_nets = []

        # check constraints in order of precedence
        for net in self.networks.values():
            if self._ip_in_subnets(src_ip, net.reject_from_src):
                continue

            if self._ip_in_subnets(src_ip, net.recv_from_src):
                dst_nets.append(net.name)
                continue

            if self._ip_in_subnets(dst_ip, net.recv_to_dst):
                dst_nets.append(net.name)
                continue

        return dst_nets

    def get_switch(self, hostname):
        pass

    def get_switch_interface(self, hostname):
        links = self.data.get("topology").get("links")
        hosts = self.data.get("topology").get("hosts")
        switch_ifaces = dict()
        for n1, n2, _ in links:
            if n1 not in hosts:
                if not switch_ifaces.has_key(n1): switch_ifaces[n1] = 0
                switch_ifaces[n1]+=1
            if n2 not in hosts:
                if not switch_ifaces.has_key(n2): switch_ifaces[n2] = 0
                switch_ifaces[n2]+=1
            if n1 == hostname:
                return n2+"-eth"+str(switch_ifaces[n2])
            if n2 == hostname:
                return n1+"-eth"+str(switch_ifaces[n1])

        return "s1-eth" + hostname.replace("h", "")

    def _get_rnd_ip(self, subnet_list):
        subnet = IPv4Network(random.choice(subnet_list))

        if subnet.numhosts == 1:
            # A /32 IPv4 network. Only one host in it.
            ip = subnet[0]
        else:
            ip = IPv4Address(random.randrange(
                int(subnet.network) + 1,
                int(subnet.broadcast) - 1
            ))

        return str(ip)

    def get_rnd_src_ip(self, network_name):
        subnet_list = self.networks.get(network_name).send_from_src
        ip = self._get_rnd_ip(subnet_list)
        self.learn_ip(str(ip), network_name)
        return ip

    def get_rnd_dst_ip(self, network_name):
        subnet_list = self.networks.get(network_name).send_to_dst
        ip = self._get_rnd_ip(subnet_list)
        self.learn_ip(str(ip), network_name)
        return ip

    def get_rnd_recv_to_ip(self, network_name):
        subnet_list = self.networks.get(network_name).recv_to_dst
        ip = self._get_rnd_ip(subnet_list)
        self.learn_ip(str(ip), network_name)
        return ip


class IPOverride(object):

    def __init__(self, oracle, profile):
        self.oracle = oracle
        self.profile = profile
        self.senders = []

        ipovr = profile.get("params").get("ip_overrides")
        self.cnt = ipovr.get("count")
        self.src_hosts = ipovr.get("src_hosts")
        self.dst_hosts = ipovr.get("dst_hosts")

        for i in range(self.cnt):
            src_host = random.choice(self.src_hosts)
            src_ip = self.oracle.get_rnd_src_ip(src_host)
            self.senders.append((src_host, src_ip))

    def get(self):
        src_host, src_ip = random.choice(self.senders)
        dst_host = random.choice(self.dst_hosts)
        dst_ip = self.oracle.get_rnd_recv_to_ip(dst_host)

        return src_host, src_ip, dst_ip


class TrafficProfile(object):
    """docstring for TrafficProfile"""

    def __init__(self, oracle, profile):
        super(TrafficProfile, self).__init__()
        self.name = profile.get("name") # name of the profile
        self.oracle = oracle # ref to the network oracle
        self.wait_for_analaysis = profile.get("wait_for_analaysis", 5)
        self.events = dict() # the event schedule, sorted by time
        self.num_events = 0 # number of events in the profile
        self.evaluation = profile.get("evaluation", "strict")
        # tolerance for progressive evaluation
        self.tolerance = profile.get("tolerance", 0.2)

        # make sure the folder for this profile exists
        self.setup_profile_dir()

        # check whether the config file exists already
        cwd = self.oracle.get_cwd()
        config_file = os.path.join(cwd, "schedule_%s.json" % self.name)
        if not os.path.exists(config_file):
            # no config file yet, we have to create the profile
            self.create_new(profile)
        else:
            self.load_from_configfile(profile, config_file)

    def setup_profile_dir(self):
        cwd = self.oracle.get_cwd()
        self.profile_dir = os.path.join(cwd, "traffic_%s" % self.name)
        if not os.path.exists(self.profile_dir):
            print ".. create profile directory for %s" % self.name
            os.mkdir(self.profile_dir)

    def load_from_configfile(self, profile, path):
        need_reload = False
        event_list = None

        with open(path, "r") as file:
            data = json.loads(file.read())
            old_profile = data.get("profile")
            event_list = data.get("schedule")

            # make sure that old and new config are the same
            # (by comparing the parameters)
            for k,v in old_profile.iteritems():
                if not profile.get(k) == v:
                    print ".. config has changed, reload"
                    need_reload = True
                    break;

        # something has changed
        if need_reload:
            # delete old stuff
            os.remove(path)
            shutil.rmtree(self.profile_dir)
            # reload
            self.setup_profile_dir()
            self.create_new(profile)
            return; #!

        # Important: the oracle has to learn the ips
        for event in event_list:
            self.oracle.learn_ip(event.get("dst_ip"), event.get("dst_host"))
            self.oracle.learn_ip(event.get("src_ip"), event.get("src_host"))

        self.create_cfg_files(event_list)
        self.num_events = len(event_list)
        #print "    events: %d" % self.num_events

    def create_cfg_files(self, events):
        """
        This is called if a new profile was created. In this case,
        after the events are known, we have to create the config files for
        the trafgen tool.

        Note: this is trafgen specific stuff (trafgen is the
        tool used for traffic generation!
        """
        skipped = 0
        created = 0
        for i, ev in enumerate(events):
            flowid = ev.get("flowid")
            if not flowid:
                raise Exception("event schedule requires flowid attribute")
#            host = self.oracle.get_host(ev.get("src"))
#            if not host:
#                raise Exception("host for ip=%s is not known" % ev.get("src"))

            # the file flowid for the trafgen config file
            cfgfile = os.path.join(self.profile_dir, flowid + ".cfg")

            # the config dict used to fill out the templates
            config = dict(
                flowid = flowid,
                time = ev.get("time"),
#                host = host,
                cfgfile = cfgfile,
                iat = ev.get("iat"),
                packets = ev.get("packets"),
                src_host = ev.get("src_host"),
                dst_host = ev.get("dst_host"),
                src_ip = ev.get("src_ip"),
                dst_ip = ev.get("dst_ip"),
                # the cfg file needs special formatting
                src_ip_repr = ", ".join(ev.get("src_ip").split(".")),
                dst_ip_repr = ", ".join(ev.get("dst_ip").split(".")),
                evaluation = ev.get("evaluation")
            )

            # put ev into the list of parsed events
            t = ev.get("time")
            if not self.events.has_key(t):
                self.events[t] = []
            self.events[t].append(config)

            # if the file already exists --> keep it
            # (I/O is critical in virtual environments)
            if os.path.exists(cfgfile):
                skipped += 1
                continue

            # create the config file for trafgen
            with open(os.path.join("templates", "template1.cfg"), "r") as file:
                data = file.read()
                cfgdata = data % config
                with open(cfgfile, "w") as cfg:
                    cfg.write(cfgdata)
                    created += 1
                time.sleep(0.05) #TODO Should be unnecessary

        #print "    cfg files skipped: %d" % skipped
        #print "    cfg files created: %d" % created


    def create_new(self, profile):
        event_list = []

        # auto means we randomly craft the traffic
        if profile.get("type") == "auto":
            self.name = profile.get("name")
            params = profile.get("params")
            events = params.get("events", 5)
            time_range = params.get("time_range", [1,10])
            choice_packets = params.get("choice_packets")
            choice_iat = params.get("choice_iat")

            if params.has_key("ip_overrides"):
                ipovr = IPOverride(self.oracle, profile)

            for i in range(events):
                time = random.randint(*time_range)
                packets = random.choice(choice_packets)

                if params.has_key("ip_overrides"):
                    src_host, src_ip, dst_ip = ipovr.get()
                else:
                    src_host = random.choice(self.oracle.get_senders())
                    src_ip = self.oracle.get_rnd_src_ip(src_host)
                    dst_ip = self.oracle.get_rnd_dst_ip(src_host)

                dst_host = self.oracle.get_expected_destination(src_ip, dst_ip)

                event = dict(
                    time = time,
                    iat = random.choice(choice_iat),
                    packets = packets,
                    flowid = "%s_%d" % (self.name, i),
                    src_host = src_host,
                    dst_host = dst_host,
                    src_ip = src_ip,
                    dst_ip = dst_ip,
                    priority = 1,
                    evaluation = self.evaluation
                )
                event_list.append(event)

            # write a config file so we can skip the create part
            # next time (if it is not enforced, e.g., by deleting the
            # profile folder)
            configfile = os.path.join(self.oracle.get_cwd(), "schedule_%s.json" % self.name)

            with open(configfile, "w") as file:
                file.write(json.dumps(dict(profile=profile, schedule=event_list), indent=2))

        self.create_cfg_files(event_list)
        self.num_events = len(event_list)

class Sender(threading.Thread):

    __TRAFGEN_PROTO = "sudo trafgen --dev %(src_host)s-eth0 --conf %(cfgfile)s"
    __TRAFGEN_PROTO_SINGLE = __TRAFGEN_PROTO + " -n 1"
    __TRAFGEN_PROTO_COUNT = __TRAFGEN_PROTO + " -n %(packets)s"
    __TRAFGEN_PROTO_TIMED_COUNT = __TRAFGEN_PROTO_COUNT + " -t %(iat)s"
    __MININET_PROTO = "m %s %s"

    def __init__(self, event):
        threading.Thread.__init__(self)
        self.event = event
        self.daemon = True

    def run(self):
        ev = dict(self.event)

        preexec_cmd = self.__TRAFGEN_PROTO_SINGLE % ev

        # Account for the packet that is sent ahead of time
        ev["packets"] -= 1

        if ev.get("iat") == -1:
            cmd = self.__TRAFGEN_PROTO_COUNT % ev
        else:
            cmd = self.__TRAFGEN_PROTO_TIMED_COUNT % ev

        # embed into mininet
        preexec_cmd = self.__MININET_PROTO % (ev.get("src_host"), preexec_cmd)
        cmd = self.__MININET_PROTO % (ev.get("src_host"), cmd)

        FNULL = open(os.devnull, 'w')

        # Send an initial packet ahead of time to give the controller
        # enough time to react
        subprocess.call([preexec_cmd],
            shell=True, stdin=None, stdout=FNULL,
            stderr=subprocess.STDOUT, cwd=os.environ["HOME"])

        time.sleep(0.5)

        subprocess.call([cmd],
            shell=True, stdin=None, stdout=FNULL,
            stderr=subprocess.STDOUT, cwd=os.environ["HOME"])

        # kill trafgens
        #os.system("ps -ef | grep %s | awk '{print $2}' | sudo xargs kill -9" % cfgfile)


class Scheduler(threading.Thread):

    def __init__(self, ):
        threading.Thread.__init__(self)
        self.daemon = True
        self.oracle = None
        self.profiles = dict()
        self.monitors = dict()

    def initialize_oracle(self, scenario_file):
        oracle = NetworkOracle(scenario_file)
        self.oracle = oracle

        info("Load Scenario: " + os.path.basename(scenario_file).replace(".yaml", "").upper())
        print ""

        # create working directory for the current scenario file
        cwd = oracle.get_cwd()
        if not os.path.exists(cwd):
            os.makedirs(cwd)

    def start_monitoring(self):
        self.monitors = dict()

        for net in self.oracle.get_networks().values():
            b = BpfBuilder()
            b.require_protocol('ip')
            b.require_protocol('udp')

            m = Monitor(net.name, net.name + '-eth0', b.compile())

            self.monitors[net] = m

        for m in self.monitors.values():
            m.start()

        time.sleep(1)

    def stop_monitoring(self):
        for m in self.monitors.values():
            m.stop()

    def evaluate_monitoring(self):
        res = dict()

        for (net, m) in self.monitors.iteritems():
            b = BpfBuilder()
            b.include_src_subnets(net.recv_from_src)
            b.include_dst_subnets(net.recv_to_dst)

            accepted = m.evaluate(b.compile())

            b = BpfBuilder()
            b.exclude_src_subnets(net.recv_from_src)
            b.exclude_dst_subnets(net.recv_to_dst)
            b.include_src_subnets(net.reject_from_src)

            rejected = m.evaluate(b.compile())

            res[net.name] = (accepted, rejected)

        return res

    def run(self):
        # print ".. initialize oracle"
        self.initialize_oracle(SCENARIO_FILE)

        if not self.oracle:
            raise Exception("Error loading scenario file")

        # Time-indexed schedule of events, each generating a portion
        # of the traffic
        schedule = dict()
        num_events = 0
        wait_for_analaysis = 0
        evaluation = "strict"
        tolerance = 1

        defined_profiles = {
            _.get("name") : _
            for _ in self.oracle.get_traffic_profiles()
        }

        # build a combined schedule
        for name in self.oracle.get_used_profiles():
            p = defined_profiles.get(name, None)

            if not p:
                print ".. WARN: traffic profile %s not found (skipped)" % name
                continue

            profile = TrafficProfile(self.oracle, p)
            num_events += profile.num_events

            if profile.evaluation == "progressive":
                # downgrade to progressive evaluation
                evaluation = profile.evaluation
                tolerance = profile.tolerance

            for schedule_time, events in profile.events.iteritems():
                if not schedule.has_key(schedule_time):
                   schedule[schedule_time] = []
                schedule[schedule_time] += events

            # aquire maximum amount of time for analysis over all profiles
            if profile.wait_for_analaysis > wait_for_analaysis:
                wait_for_analaysis = profile.wait_for_analaysis

        # Suppress evaluation of an empty traffic schedule
        if not schedule:
            self._update_task(None, [])
            return 

        self.start_monitoring()
        time_index = 0
        time.sleep(1)
        done = 0

        # the amount of traffic we expect to see at each host
        exp_sent = dict()
        exp_recv = dict()

        for host in self.oracle.get_hosts():
            exp_sent[host] = 0
            exp_recv[host] = 0

        threads = []

        while schedule:
            if schedule.has_key(time_index):
                for event in schedule.get(time_index):
                    done += 1
                    msg = (".. [%(src_host)6s->%(dst_host)6s] %(src_ip)15s --> %(dst_ip)15s (%(packets)d pkts)" % event) + " | %d/%d" % (done, num_events)
                    print colored(msg, "cyan")
                    thread = Sender(event)
                    thread.start()
                    threads.append(thread)

                    # update packet statistics
                    src_ip = event.get("src_ip")
                    dst_ip = event.get("dst_ip")
                    src_host = event.get("src_host")
                    packets = event.get("packets")

                    if event.get("evaluation") in ("strict", "progressive"):
                        if src_host:
                            exp_sent[src_host] += packets

                        dst_hosts = self.oracle.get_expected_destinations(
                            src_ip, dst_ip
                        )

                        for dst_host in dst_hosts:
                            exp_recv[dst_host] += packets

                del schedule[time_index]

            time.sleep(1)
            time_index += 1

        # reduce total packet count by the expected packet_ratio
        # for each destination host
        exp_recv = {
            host : int(packets * self.oracle.networks[host].packet_ratio)
            for host, packets in exp_recv.iteritems()
        }

        for thread in threads:
            thread.join()

        time.sleep(wait_for_analaysis)

        self.stop_monitoring()
        stats = self.evaluate_monitoring()

        feedback = []

        infomsg   = "Info:  {:d} packets expected at {:s} ({:d} received)"
        err_exp   = "Error: {:d} packets expected at {:s} ({:d} received)"
        err_unexp = "Error: {:d} unexpected packets recevied at {:s}"

        # check recv stats
        if evaluation == "progressive":
            # progressive evaluation
            status = "success"

            for host, expected in exp_recv.iteritems():
                if host not in stats:
                    continue

                accepted, rejected = stats.get(host)

                if accepted > expected * (1.0 + tolerance):
                    status = "failure"
                    msg = err_exp.format(expected, host, accepted)
                    feedback.append(("red", msg))
                elif accepted < expected * (1.0 - tolerance):
                    status = "failure"
                    msg = err_exp.format(expected, host, accepted)
                    feedback.append(("red", msg))
                elif abs(accepted - expected) > 1:
                    msg = infomsg.format(expected, host, accepted)
                    feedback.append(("green", msg))

                if rejected != 0:
                    status = "failure"
                    msg = err_unexp.format(rejected, host)
                    feedback.append(("red", msg))
        else:
            # strict evaluation
            status = "success"

            for host, expected in exp_recv.iteritems():
                if host not in stats:
                    continue

                accepted, rejected = stats.get(host)

                if abs(accepted - expected) > tolerance:
                    status = "failure"
                    msg = err_exp.format(expected, host, accepted)
                    feedback.append(("red", msg))

                if rejected != 0:
                    status = "failure"
                    msg = err_unexp.format(rejected, host)
                    feedback.append(("red", msg))

        print ""

        for color, line in feedback:
            print "   {:s}".format(colored(line, color))

        print ""

        if status == "success":
            print "   Status:", colored("SUCCESS", "green")
        elif status == "failure":
            print "   Status:", colored("FAILURE", "red")

        self._update_task(status, feedback)

    def _update_task(self, status, errors):
        # cleanup
        os.system("rm -f tmp_result_*")

        tmpfile = os.path.join(os.getcwd(), "tmp_result_%s.yaml" % time.time())

        with open(tmpfile, "w") as file:
            file.write(yaml.dump(dict(status = status, errors = errors)))

        os.system("runuser -l %s -c '/vagrant_data/remote/script_restart_task.sh true %s %s'" % (os.environ["SUDO_USER"], TASK_FILE, tmpfile))

if __name__ == '__main__':
    thread = Scheduler()
    thread.start()

    # keep main thread alive
    while True:
        time.sleep(1)
