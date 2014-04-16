.. _deployment:

Deployment
##########

Although the Circus daemon can be managed with the circusd command, it's
easier to have it start on boot. If your system supports Upstart, you can
create this Upstart script in /etc/init/circus.conf.

::

    start on filesystem and net-device-up IFACE=lo
    stop on runlevel [016]

    respawn
    exec /usr/local/bin/circusd /etc/circus/circusd.ini

This assumes that circusd.ini is located at /etc/circus/circusd.ini. After
rebooting, you can control circusd with the service command::

    # service circus start/stop/restart

If your system supports systemd, you can create this systemd unit file under
/etc/systemd/system/circus.service.

::

   [Unit]
   Description=Circus process manager
   After=syslog.target network.target nss-lookup.target

   [Service]
   Type=simple
   ExecReload=/usr/bin/circusctl reload
   ExecStart=/usr/bin/circusd /etc/circus/circus.ini
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=default.target

A reboot isn't required if you run the daemon-reload command below::

    # systemctl --system daemon-reload

Then circus can be managed via::

    # systemctl start/stop/status/reload circus


Recipes
=======

This section will contain recipes to deploy Circus. Until then you can look at
Pete's `Puppet recipe <https://github.com/fetep/puppet-circus>`_ or at Remy's
`Chef recipe
<https://github.com/novagile/insight-installer/blob/master/chef/cookbooks/insight/recipes/circus.rb>`_
