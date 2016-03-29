cd Volatility/volatility/plugins
find . -type f -print0 | xargs -0 sed -i 's/def calculate(self):/def calculate(self, addr_space=None):/g'
find . -type f -print0 | xargs -0 sed -i 's/def render_text(self, outfd, data):/def render_text(self, outfd, data, addr_space=None):/g'
find . -type f -print0 | xargs -0 sed -i 's/^        addr_space = utils/        if addr_space is None:\n            addr_space = utils/g'
find . -type f -print0 | xargs -0 sed -i 's/^        address_space = utils/        if addr_space is not None:\n            address_space = addr_space\n        else:\n            address_space = utils/g'
