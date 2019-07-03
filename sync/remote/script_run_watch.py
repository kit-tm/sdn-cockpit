import time
import os
import yaml
import threading
import logging
import hashlib
import glob
from termcolor import colored

class CommandProcessor(object):
    """docstring for CommandProcessor"""

    def __init__(self):
        super(CommandProcessor, self).__init__()
        self.processors = [
            dict(aliase=["#tm"], run=self.__tm)
        ]

    def run(self, filedata, path):
        flag = False
        cmd = dict(
            path=path
        )
        for line in filedata.split(os.linesep):
            cmd_line = line.strip()
            if len(cmd_line)>0:
                if cmd_line[0] == "#":
                    new_cmd = self.parse_line(cmd_line, path)
                    if new_cmd:
                        cmd.update(new_cmd)
        return cmd

    def parse_line(self, cmd_line, path):
        c = cmd_line.split(" ")
        if len(c) > 0:
            alias = c[0]
            for p in self.processors:
                if alias in p.get("aliase"):
                    params = cmd_line.replace(alias, "").split(" ");
                    if len(params) > 0:
                        stripped_params = []
                        stripped_flags = []
                        stripped_keys = dict()
                        for el in params:
                            el = el.strip()
                            if len(el) > 0:
                                # example: param=13
                                if "=" in el:
                                    data = el.split("=")
                                    if len(data) == 2:
                                        stripped_keys[data[0]] = data[1]

                                if "-" in el:
                                    stripped_flags.append(el.replace("-", ""))
                                elif "--" in el:
                                    stripped_flags.append(el.replace("--", ""))
                                else:
                                    stripped_params.append(el)

                        return p.get("run")(stripped_params, stripped_flags, stripped_keys, path)
        return None

    def __tm(self, params, flags, kwargs,  path):
        cmd = dict(
            cmd="proxy_command",
            path=path,
            params=params,
            flags=flags,
            kwargs=kwargs)
        return cmd

class CommandInterpreter(object):

    def __init__(self):
        pass

    def get_path_controller(self, path):
        """  take a local controller file and return the remote controller file  """
        folders = path.split(os.sep)
        usepath = []
        for dirname in reversed(folders):
            usepath.append(dirname)
            if dirname == "local":
                break;
        result = os.path.join(os.getcwd(), os.sep.join(reversed(usepath)))
        return result

    def get_path_task(self, taskname):
        """ take a local controller path and a task name and return the corresponding remote task file """
        if not taskname.endswith(".yaml"):
            taskname += ".yaml"
        return os.path.join(os.getcwd(), "local", "apps", "tasks", taskname)

    def get_path_scenario(self, scenario):
        if not scenario.endswith(".yaml"):
            scenario += ".yaml"
        return os.path.join(os.getcwd(), "local", "apps", "scenarios", scenario)

    def check_topology(self, scenariofile):
        """ returns true if the topology has to be changed """

        if not scenariofile: return False;
        if not os.path.exists(scenariofile): return False;
        topologyfile = os.path.join(os.getcwd(), "tmp_topology.mn")
        if not os.path.exists(topologyfile): return True;

        topology = None
        try:
            with open(scenariofile,"r") as file:
                topology = yaml.dump(yaml.safe_load(file.read()).get("root").get("topology"))
        except:
            return False

        current_topology = None
        topologyfile = os.path.join(os.getcwd(), "tmp_topology.mn")
        with open(topologyfile, "r") as file:
            current_topology=file.read()

        # only restart mininet of topology changed
        return current_topology != topology

    def on_save_host_hook(self, scenariofile):
        if scenariofile is None: return
        with open(scenariofile,"r") as file:
            root = yaml.safe_load(file.read()).get("root")
            hook = root.get("on-save-host-hook")
            if hook is None:
                return
            for host in root.get("topology").get("hosts"):
                name = host.get("name")
                os.system("m {} {}".format(name, hook))


    def run(self, cmd):
        params = cmd.get("params")
        kwargs = cmd.get("kwargs")

        controller = None
        scenario = None
        task = None

        # reload controller (always)
        controller = self.get_path_controller(cmd.get("path"))
        print colored('.. controller: %s' % controller, 'white')

        if not kwargs:
            print colored('.. controller: not an application', 'white')
            return

        # a task is specified
        if kwargs.has_key("task"):
            # reload task
            task = self.get_path_task(kwargs.get("task"))
            # get scenario file
            scenario = None
            if os.path.exists(task):
                parsed = None
                try:
                    with open(task, "r") as file:
                        parsed = yaml.safe_load(file.read())
                        scenario = parsed.get("task").get("scenario")
                        scenario = self.get_path_scenario(scenario)
                except Exception as e:
                    print ".. error: couldn't extract scenario file from task"
        # scenario is specified
        if kwargs.has_key("scenario"):
            name =kwargs.get("scenario")
            print colored('.. scenario: %s' %name, 'white')
            scenario = self.get_path_scenario(name)

        print ""

        topology_change = self.check_topology(scenario)
        if topology_change:
            os.system("exec remote/script_stop_all.sh")
            time.sleep(3) #TODO unnecessary?
            os.system("exec remote/script_restart_mininet.sh true %s" % scenario)
            #time.sleep(5)

        if task:
            os.system("exec remote/script_restart_task.sh true %s" % task)
            os.system("exec remote/script_restart_controller.sh true %s" % controller)
            os.system("exec remote/script_restart_scenario.sh true %s %s" % (scenario, task))
            self.on_save_host_hook(scenario)
            return

        if controller:
            os.system("exec remote/script_restart_controller.sh true %s" % controller)
        if scenario:
            os.system("exec remote/script_restart_scenario.sh true %s" % scenario)
            self.on_save_host_hook(scenario)

class Watch(threading.Thread):

    def __init__(self, **kwargs):
        super(Watch, self).__init__()
        self.daemon = True
        self.active = True
        self.files = dict()

    def add_dir(self, path):
        pass

    def run(self):

        # create watch for all application directories
        watchpath = os.path.join(os.getcwd(), "local", "apps", "src")
        print colored('.. watch %s' % watchpath, 'white')
        for f in glob.glob(os.path.join(watchpath, "*.py")):
            self.files[f] = os.path.getmtime(f)

        cnt=0
        # main loop
        while self.active:
            processor = CommandProcessor()
            interpreter = CommandInterpreter()

            # check for new files every 10 interations
            cnt += 1
            if cnt%10 == 0:
                active = self.files.keys()
                for f in glob.glob(os.path.join(watchpath, "*.py")):
                    if not f in active:
                        print colored('.. file added %s' % f, 'white')
                        self.files[f] = os.path.getmtime(f)

            remove = []
            for path, timestamp in self.files.iteritems():
                try:
                    ft= os.path.getmtime(path)
                    if ft > timestamp:
                        self.files[path] = ft
                        print path, "changed"

                        with open(path, "r") as file:
                            data = file.read()
                            cmd = processor.run(data, path)
                            interpreter.run(cmd)

                except OSError as e:
                    remove.append(path)

            if len(remove) > 0:
                for path in remove:
                    print colored('.. file removed %s' % path, 'white')
                    del self.files[path]

            time.sleep(0.1)


watch = Watch()
watch.start()

# avoids return and enables strg+c
while True:
    time.sleep(1)
