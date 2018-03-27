import sys
import os
import yaml
import time
import subprocess
import tempfile
import itertools
from termcolor import colored
from terminaltables import AsciiTable
from ansiwrap import ansilen
from textwrap import fill, dedent

def ansiljust(string, length):
    return string + (' ' * max(0, length - ansilen(string)))

def side_by_side(a, b, pad):
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    max_line = max([ansilen(a_line) for a_line in a_lines])
    return '\n'.join([ansiljust(a_line, max_line+pad) + b_line
                      for a_line, b_line
                      in itertools.izip_longest(a_lines, b_lines, fillvalue='')])

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

if len(sys.argv) > 1:
    taskfile = sys.argv[1]
    resultfile = None

    if len(sys.argv) == 3:
        resultfile = sys.argv[2]

    if not os.path.exists(taskfile):
        info("There is currently no task selected")
        print ""
        print "    Select an application (or create a new one) and add the"
        print "    [#tm task=taskname] makro to start task. Please contact your"
        print "    supervisor if there are any problems!"
        while True:
            time.sleep(10) # don't return

    parsed = None

    try:
        with open(taskfile, "r") as file:
            parsed = yaml.load(file.read())
    except Exception as e:
        panic("Taskfile %s invalid (could not be parsed); %s" % (taskfile, str(e)))

    # seems to be a valid task file, print info
    task = parsed.get("task")

    information = dedent("""
    %(ltask)s %(task)s
    %(lscenario)s %(scenario)s
    %(ldescription)s
    %(description)s
    %(lresult)s %(result)s
    """)

    data = {
        'ltask': colored("Task:", attrs=["bold"]),
        'lscenario': colored("Scenario:", attrs=["bold"]),
        'ldescription': colored("Description:", attrs=["bold"]),
        'lresult': colored("Result:", attrs=["bold"]),
        'task': task.get("name"),
        'scenario': task.get("scenario"),
        'description': fill(task.get("description"), 30, break_long_words=False),
    }

    if resultfile:
        try:
            with open(resultfile, "r") as file:
                parsed = yaml.load(file.read())

                # parsed.get("status") == None is allowed
                # It won't generate a status line

                if parsed.get("status") is None:
                    data['result'] = colored("No Scenario")
                elif parsed.get("status") == "failure":
                    data['result'] = colored("FAILURE", "red")
                elif parsed.get("status") == "success":
                    data['result'] = colored("SUCCESS", "green")
        except Exception as e:
            panic("ResultFile %s invalid (could not be parsed); %s" % (resultfile, str(e)))
    else:
        data['result'] = colored("IN PROGRESS", "yellow")

    if "graph" in task:
        with tempfile.NamedTemporaryFile() as in_file, tempfile.TemporaryFile() as out_file:
            in_file.write(task['graph'])
            in_file.flush()
            out_file.write("\n%s\n\n" % colored("Topology:", attrs=["bold"]))
            out_file.flush()
            subprocess.call(["graph-easy %s" % in_file.name],
                shell=True, stdin=None, stdout=out_file,
                stderr=subprocess.STDOUT, cwd="/home/vagrant")
            out_file.seek(0)

            print side_by_side(information % data, out_file.read(), 1)
    else:
        print information % data

    while True:
        time.sleep(10) # don't return

else:
    panic("No task file specified.")
