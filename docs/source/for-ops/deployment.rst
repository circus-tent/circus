Deployment
##########

Although the Circus daemon can be managed with the circusd command, it's
easier to have it start on boot. If your system supports Upstart, you can
create this Upstart script in /etc/init/circus.conf.

::

    start on filesystem and net-device-up IFACE=lo

    stop on shutdown

    respawn
    exec /usr/local/bin/circusd --log-output /var/log/circus.log \
                                --pidfile /var/run/circusd.pid \
                                /etc/circus.ini

This assumes that circus.ini is located at /etc/circus.ini. After
rebooting, you can control circusd with the service command::

    $ service circus start/stop/restart

Recipes
=======

This section will contain recipes to deploy Circus. Until then you can look at
Pete's `Puppet recipe <https://github.com/fetep/puppet-circus>`_ or at Remy's
`Chef recipe
<https://github.com/novagile/insight-installer/blob/master/chef/cookbooks/insight/recipes/circus.rb>`_
