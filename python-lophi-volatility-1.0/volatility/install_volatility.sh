# PyCrypto
echo "Installing pycrypto..."
pip install --no-index --find-links file://lophi/pypi/ pycrypto

# Distorm
echo "Installing distorm3..."
pip install --no-index --find-links file://lophi/pypi/ distorm3

# Yara
echo "Installing yara..."
tar -xvzf yara-1.4.tar.gz
rm yara-1.4.tar.gz
cd yara-1.4
./configure
make
make install
cd ..

# pyyara
echo "Install pyyara..."
pip install --no-index --find-links file://lophi/pypi/ yara

# Ubuntu hack
echo "Updating ld..."
echo "/usr/local/lib" >> /etc/ld.so.conf
ldconfig

echo "Installing volatility..."
cd Volatility
sudo python setup.py install

echo "Done!"
