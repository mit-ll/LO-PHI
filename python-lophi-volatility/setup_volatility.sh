# Deps
echo "Downloading Subversion..."
sudo apt-get install subversion pcregrep libpcre++-dev python-dev python-pip -y

echo "Downloading pip packages..."
mkdir pypi
pip install --no-install --download pypi pycrypto
pip install --no-install --download pypi distorm3
pip install --no-install --download pypi yara

cd volatility

echo "Downloading yara..."
wget http://yara-project.googlecode.com/files/yara-1.4.tar.gz

echo "Getting volatility..."
svn checkout http://volatility.googlecode.com/svn/trunk Volatility

# Malware plugins
echo "Installing volatility malware plugins..."
cd Volatility/volatility/plugins
wget http://malwarecookbook.googlecode.com/svn/trunk/malware.py
cd ../../..

echo "Installing LO-PHI address space..."
cp lophiaddressspace.py Volatility/volatility/plugins/addrspaces/

echo "Patching volatilty to reuse the same address space..."
./replace_calculate.sh

