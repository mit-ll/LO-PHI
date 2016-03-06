#!/bin/bash
# Update bashrc
if grep -q "# LO-PHI" ~/.bashrc
then
   echo "LO-PHI PYTHONPATH variables are already set."
else
   echo "# LO-PHI" >> ~/.bashrc
   echo "export PYTHONPATH=\$PYTHONPATH:$PWD/python-lophi-1.0" >> ~/.bashrc
   echo "export PYTHONPATH=\$PYTHONPATH:$PWD/python-lophi-semanticgap-1.0" >> ~/.bashrc
   echo "export PYTHONPATH=\$PYTHONPATH:$PWD/lophi-net-services-1.0" >> ~/.bashrc
   echo "export PYTHONPATH=\$PYTHONPATH:$PWD/lophi-automation-1.0" >> ~/.bashrc
   echo "export PYTHONPATH=\$PYTHONPATH:$PWD/lophi-analysis-1.0" >> ~/.bashrc
   source ~/.bashrc
fi

# Setup a web server share
read -p "Do you wish to create a webserver link for SUT software? [y/n]" yn
case $yn in
    [yY]* ) echo "Creating symbolic link at /var/ww/html/lophi/..."
            sudo ln -s $PWD/sut_software /var/www/html/lophi;;
    [nN]* ) exit;;
esac


