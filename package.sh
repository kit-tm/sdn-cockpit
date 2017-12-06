#!/bin/bash
set -e

pushd package
vagrant up
vagrant package --vagrantfile Vagrantfile-local --output sdnlab.box
vagrant destroy -f
mv sdnlab.box ../
popd
