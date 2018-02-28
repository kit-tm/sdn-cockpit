#!/usr/bin/env bash

# Fix locales -.-
sudo locale-gen en_US.UTF-8
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
echo 'export LC_ALL="en_US.UTF-8"' >> /home/ubuntu/.bashrc
echo 'export LC_CTYPE="en_US.UTF-8"' >> /home/ubuntu/.bashrc

# Install required packages
sudo apt-get update -y
sudo apt-get install -y --install-recommends \
git \
libgraph-easy-perl \
htop \
iputils-ping \
ncurses-term \
netcat \
netsniff-ng \
python \
python-pip \
tcpdump \
tmux

# Install ryu controller framework
git clone https://github.com/osrg/ryu.git
pushd ryu
sudo -H pip install .
popd

# Install mininet
git clone https://github.com/mininet/mininet.git
./mininet/util/install.sh -nfv
sudo cp ./mininet/util/m /usr/local/bin/

# Update global profile
echo 'export PATH=/vagrant_data/remote:$PATH' >> /etc/profile.d/vagrant_data.sh

# Update bashrc
echo 'alias mininet=mn' >> /home/ubuntu/.bashrc
echo 'cd /vagrant_data' >> /home/ubuntu/.bashrc

# Update tmux.conf
echo 'set-option -g mouse on' >> /home/ubuntu/.tmux.conf
chown ubuntu:ubuntu /home/ubuntu/.tmux.conf

# Adjust TERM for cygwin to match terminfo database entry
echo '[ "$TERM" == "cygwin" ] && export TERM=cygwinB19' >> /home/ubuntu/.profile

# Install python packages
sudo pip install ansiwrap termcolor terminaltables Pyro4 requests psutil ipaddr pyyaml

# Remove unused directories
sudo rm -rf \
/home/ubuntu/mininet \
/home/ubuntu/openflow \
/home/ubuntu/ryu

# Remove unused packages
sudo apt-get remove -y --autoremove \
*-dev \
git \
linux-headers-* \
python3 \
python-pip

# Remove APT cache
sudo apt-get clean -y
sudo apt-get autoclean -y

# Cleanup log files
find /var/log -type f | while read f; do echo -ne '' > $f; done;

# Zero free space to aid VM compression
#sudo dd if=/dev/zero of=/EMPTY bs=1M
#sudo rm -f /EMPTY
