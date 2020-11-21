#!/usr/bin/env bash

# Fix locales -.-
sudo locale-gen en_US.UTF-8
export LC_ALL="en_US.UTF-8"
export LC_CTYPE="en_US.UTF-8"
echo 'export LC_ALL="en_US.UTF-8"' >> /home/vagrant/.bashrc
echo 'export LC_CTYPE="en_US.UTF-8"' >> /home/vagrant/.bashrc

# Install required packages
sudo apt-get update -y
sudo apt-get install -y --install-recommends \
git \
net-tools \
libgraph-easy-perl \
htop \
iputils-ping \
arping \
ncurses-term \
netcat \
netsniff-ng \
python3 \
python3-pip \
tcpdump \
tmux \
dos2unix
# dos2unix is only here in case there is trouble with shared folders to windows

sudo -H pip3 install ryu

# Install mininet
git clone https://github.com/mininet/mininet.git
pushd ./mininet/util
./install.sh -nfv
popd
sudo cp ./mininet/util/m /usr/local/bin/
rm -rf ./mininet/

# Update global profile
echo 'export PATH=/vagrant_data/remote:$PATH' >> /etc/profile.d/vagrant_data.sh

# Update bashrc
echo 'alias mininet=mn' >> /home/vagrant/.bashrc
echo 'cd /vagrant_data' >> /home/vagrant/.bashrc

# Update tmux.conf
echo 'set-option -g mouse on' >> /home/vagrant/.tmux.conf
chown vagrant:vagrant /home/vagrant/.tmux.conf

# Adjust TERM for cygwin to match terminfo database entry
echo '[ "$TERM" == "cygwin" ] && export TERM=cygwinB19' >> /home/vagrant/.profile

# Install python packages
sudo pip3 install ansiwrap termcolor terminaltables Pyro4 requests psutil ipaddr pyyaml

# Remove unused directories
sudo rm -rf \
/home/vagrant/mininet \
/home/vagrant/openflow \
/home/vagrant/ryu

# Remove unused packages
sudo apt-get remove -y --autoremove \
*-dev \
git \
linux-headers-* \
python3-pip

# Remove APT cache
sudo apt-get clean -y
sudo apt-get autoclean -y

# Cleanup log files
find /var/log -type f | while read f; do echo -ne '' > $f; done;

# Zero free space to aid VM compression
#sudo dd if=/dev/zero of=/EMPTY bs=1M
#sudo rm -f /EMPTY
