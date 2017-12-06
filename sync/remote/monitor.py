#!/usr/bin/env python2.7

import re

from os import setsid
from shlex import split
from subprocess import Popen, PIPE
from signal import SIGINT
from tempfile import TemporaryFile
from time import sleep


class BpfBuilder(object):

    def __init__(self):
        self.required_protocols = []
        self.included_src_subnets = []
        self.included_dst_subnets = []
        self.excluded_src_subnets = []
        self.excluded_dst_subnets = []

    def include_src_subnet(self, net):
        self.included_src_subnets.append(net)
        return self

    def include_dst_subnet(self, net):
        self.included_dst_subnets.append(net)
        return self

    def include_src_subnets(self, nets):
        for _ in nets:
            self.include_src_subnet(_)
        return self

    def include_dst_subnets(self, nets):
        for _ in nets:
            self.include_dst_subnet(_)
        return self

    def exclude_src_subnet(self, net):
        self.excluded_src_subnets.append(net)
        return self

    def exclude_dst_subnet(self, net):
        self.excluded_dst_subnets.append(net)
        return self

    def exclude_src_subnets(self, nets):
        for _ in nets:
            self.exclude_src_subnet(_)
        return self

    def exclude_dst_subnets(self, nets):
        for _ in nets:
            self.exclude_dst_subnet(_)
        return self

    def require_protocol(self, proto):
        """ All (succesively specified) protocols given via this
            method must be present in packets that shall be monitored.
        """
        self.required_protocols.append(proto)
        return self

    def compile(self):
        protos = ' and '.join(self.required_protocols)

        in_nets  = ['src net {:s}'.format(_) for _ in self.included_src_subnets]
        in_nets += ['dst net {:s}'.format(_) for _ in self.included_dst_subnets]
        in_nets  = ' or '.join(in_nets)
        in_nets  = '({:s})'.format(in_nets) if in_nets else ''

        ex_nets  = ['src net {:s}'.format(_) for _ in self.excluded_src_subnets]
        ex_nets += ['dst net {:s}'.format(_) for _ in self.excluded_dst_subnets]
        ex_nets  = ' or '.join(ex_nets)
        ex_nets  = 'not ({:s})'.format(ex_nets) if ex_nets else ''

        filter = ' and '.join(_ for _ in [protos, in_nets, ex_nets] if _)

        return filter


class Monitor(object):

    M       = '/usr/local/bin/m'
    KILL    = '/bin/kill'
    TCPDUMP = '/usr/sbin/tcpdump'

    RE_CAPTURED = re.compile('([\d]+) packets captured\n', re.MULTILINE)

    @staticmethod
    def execute(cmd, stdin = None, stdout = None):
        p = Popen(cmd, cwd = '/tmp', shell = True, stdin = stdin,
                stdout = stdout)
        p.wait()

        return p

    def __init__(self, net, interface, bpf = None):
        """ net:        the mininet host to be monitored
            interface:    the interface name within the mininet host from
                        which packets are captured
            bpf:        the berkeley packet filter expression that defines
                        acceptable packets
        """
        self.net = net
        self.interface = interface
        self.bpf = bpf
        self.process = None
        self.pcapfile = TemporaryFile(suffix = '.pcap')

    def start_capture(self):
        cmd  = self.M + ' {:s}'.format(self.net)
        cmd += ' ' + self.TCPDUMP + ' -n -s 48 -B 16384'
        cmd += ' ' + '-i {:s}'.format(self.interface)
        cmd += ' ' + '-w -'

        if self.bpf:
            cmd += ' ' + '"{:s}"'.format(self.bpf)

        # Special invocation for a background task.
        # preexec_fn = setsid is required. Otherwise signals will not
        # be deliviered to the process.
        return Popen(split(cmd), cwd = '/tmp', stdout = self.pcapfile,
            stderr = PIPE, preexec_fn = setsid)

    def stop_capture(self):
        # We cannot use the send_signal method of the process object
        # at this time, so we send a SIGINT via the kill command.
        cmd  = self.M + ' {:s}'.format(self.net)
        cmd += ' ' + self.KILL + ' -s INT'
        cmd += ' ' + '{:d}'.format(self.process.pid)

        self.execute(cmd)

    def start(self):
        self.process = self.start_capture()

    def stop(self):
        self.stop_capture()
        self.process.wait()

    def evaluate(self, bpf = ''):
        cmd  = self.TCPDUMP + ' -nr - "' + bpf + '"'
        cmd += ' 2> /dev/null | wc -l'

        self.pcapfile.seek(0)

        p = self.execute(cmd, stdin = self.pcapfile, stdout = PIPE)

        return int(''.join(p.stdout))


if __name__ == '__main__':
    m = Monitor('net2', 'net2-eth0', 'ip and udp and host 38.92.124.79')

    m.start()
    sleep(1)
    m.stop()
    r = m.evaluate()

    print(r)
