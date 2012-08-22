.. _cluster:

Running Circus in a Cluster
###########################

Circus can be run with a single master issuing commands to the worker nodes.  This allows an administrator to control nodes by sending commands to the master instead.  The cluster allow aggregates the individual stats streams of the workers to allow viewing the processes of the entire cluster in a single **circus-top** window.

circusd-cluster
===============

The command **circusd-cluster** is used to execute a master process.  The syntax is **circusd-cluster <config_file>**.

A config file might look as follows:

    [circus-cluster]
    endpoint = tcp://127.0.0.1:5558
    stats_endpoint = tcp://127.0.0.1:5559

    [node:first]
    endpoint = tcp://127.0.0.1:5555
    pubsub_endpoint = tcp://127.0.0.1:5556
    stats_endpoint = tcp://127.0.0.1:5557

If a node is specified in the config file, it should be running when **circusd-cluster** is executed in order to register the node as part of the cluster.

A command can be sent to the node **first** by the master by running **circusctl** and specifying the node name with the **--node** option:

    circusctl incr dummy --endpoint tcp://127.0.0.1:5558 --node first

Specifying cluster membership in worker config file
===================================================

If you want a node to register with a master node upon running **circusd**, simply specify the parameters to identify the master in the worker's config file:

    [circus]
    check_delay = 5
    endpoint = tcp://127.0.0.1:6555
    pubsub_endpoint = tcp://127.0.0.1:6556
    stats_endpoint = tcp://127.0.0.1:6557
    node = second
    master = tcp://127.0.0.1:5558

Specifying cluster membership in command line
=============================================

Suppose a worker node is already running and you want it to join a cluster.  Use the **register_node** command to tell the master node to join the worker to the cluster.  The syntax is **circusctl register_node <node_name> <node_endpoint> <node_stats_endpoint>**.

For example:

    circusctl register_node second tcp://127.0.0.1:6555 tcp://127.0.0.1:6557 --endpoint tcp://127.0.0.1:5558


