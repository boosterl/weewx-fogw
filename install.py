# installer for the weewx-fogw driver
# Copyright 2022 Bram Oosterlynck, all rights reserved
# Distributed under the terms of the GNU Public License (GPLv3)

from weecfg.extension import ExtensionInstaller

def loader():
    return FogwInstaller()

class FogwInstaller(ExtensionInstaller):
    def __init__(self):
        super(FogwInstaller, self).__init__(
            version="0.1",
            name='FoGW',
            description='Fetch data from Fine Offset WiFi gateways (GW1000, GW1100, GW2000)',
            author="Bram Oosterlynck",
            author_email="bram.oosterlynck@gmail.com",
            files=[('bin/user', ['bin/user/fogw.py'])]
        )
