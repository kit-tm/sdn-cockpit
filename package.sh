#!/bin/bash
set -e

pushd package
vagrant up
vagrant package --vagrantfile Vagrantfile-local --output sdn-cockpit.box
vagrant destroy -f
mv sdn-cockpit.box ../
popd
