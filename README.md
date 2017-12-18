# sdn-cockpit

sdn-cockpit is an open-source teaching framework for Software-defined Networking (SDN) developed by the Institute of Telematics, Karlsruhe Insitute of Technology.

The tool provides an easy-to-use environment for fast pace SDN application development with special support for executing automated evaluation scenarios. It builds on the mininet emulator (https://github.com/mininet/mininet) and the Ryu controller software (https://github.com/osrg/ryu). Vagrant is used for automatic deployment (https://www.vagrantup.com/).

## Installation

sdn-cockpit supports Linux, macOS and Windows. It depdends on Vagrant and VirtualBox (https://www.virtualbox.org/), which need to be installed beforehand. Install sdn-cockpit with:

    git clone https://github.com/KIT-Telematics/sdn-cockpit.git
    cd sdn-cockpit
    vagrant up

### Known issues while using Windows as host operating system

#### vagrant ssh not working properly

It seems that ``vagrant ssh`` is currently not working properly. While the login into the virtual machine works, commands are not execpted as expected. There is an easy workaround using the putty tool following these instructions: https://github.com/Varying-Vagrant-Vagrants/VVV/wiki/Connect-to-Your-Vagrant-Virtual-Machine-with-PuTTY


#### run.sh script doesn't work

There is an issue with windows-style line endings. Currently, the only way to fix this is to run the following three commands inside the VM (i.e., after using ``vagrant ssh`` or putty):

``
sudo apt-get install dos2unix
cd vagrant_data
find ./ -type f -exec dos2unix {} \;
``

## Quickstart

Enter the virtual machine and execute sdn-cockpit:

    vagrant ssh
    bash run.sh

sdn-cockpit will now present a default view where no task is loaded. To load a task, open the folder ``sync/local/apps/src/`` outside of the virtual machine and edit the corresponding task files with your favorite text editor. It must support unix-style line endings, e.g. Notepad++ (https://notepad-plus-plus.org/) for Windows. Upon saving, sdn-cockpit will automatically load the respective task and start evaluating your current solution.

## Manual

You can find a comprehensive manual with more detailed installation and usage instructions [here](doc/manual.pdf). It also includes a guide on writing Ryu-based SDN-applications.
