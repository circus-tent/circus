/**
 * Display the given data into the specified id and refreshs it every N
 * seconds, where N is specified by the delay parameter.
 *
 * @param string: id the selector used to create the svg object into.
 * @param array: to_display the data to display.
 * @param string: css_class the css class to apply to the svg element created.
 * @param int: width the with in pixels.
 * @param int: height the height in pixels.
 * @param int: delay the delay before refreshs of the graph.
 **/
function displayGraph(id, to_display, css_class, width, height, delay) {
    var graph = d3.select(id).append('svg:svg').attr('width', '100%')
                  .attr('height', '100%').attr('class', css_class);

    // compute the scales of the graph
    var x = d3.scale.linear().domain([0, to_display.length])
                             .range([-5, width]);

    var y = d3.scale.linear().domain([0, 100]).range([0, height]);

    var line = d3.svg.line().x(function(d, i) { return x(i); })
                            .y(function(d) { return y(d); })
                            .interpolate('basis');

    graph.append('svg:path').attr('d', line(to_display));

    function redrawWithAnimation() {
        // change the value of the labels for last_{mem, cpu} ...
        var last_value = parseInt(to_display[to_display.length - 5]);
        $(id + '_last_' + css_class).text(last_value + '%');

        // ... and redraw the graph
        graph.selectAll('path')
             .data([to_display])
             .attr('transform', 'translate(' + x(1) + ')')
             .attr('d', line)
             .transition()
             .ease('linear')
             .duration(delay)
             .attr('transform', 'translate(' + x(0) + ')');
    }

    setInterval(redrawWithAnimation, delay);
}

/**
 * Create an array and fill it with zeros.
 *
 * @param size: the size of the array to create.
 **/
function zeroFilledArray(size) {
    var array = [];
    for (i = 0; i < size; i++) { array[i] = 0; }
    return array;
}

/**
* Get information from the socket and create a graph from there.
*
* @param socket the socket object.
* @param watcher the name of the watcher we want to get stats from.
* @param id the css selector to generate the graph into.
**/
function addWatcher(socket, watcher, id) {
    if (id === undefined) {
        id = '#' + watcher;
    }
    // before starting the socket with the server, initiate the data
    // structures that will be used to store the data
    var data = { mem: zeroFilledArray(25),
                 cpu: zeroFilledArray(25) };

    var stream = 'stats-' + watcher;

    socket.on(stream, function(args) {
        if (args.cpu > 100) { args.cpu = 100; }
        if (args.mem > 100) { args.mem = 100; }
        data.cpu.shift();
        data.cpu.push(args.cpu);
        data.mem.shift();
        data.mem.push(args.mem);
    });

    displayGraph(id, data.cpu, 'cpu', 320, 50, 1000);
    displayGraph(id, data.mem, 'mem', 320, 50, 1000);
}


/**
 * High level API to supervise watchers.
 *
 * This function listen to some specific streams and start the generation of
 * the graphs and their update.
 *
 * @param socket: the socket object to use.
 * @param watchers: the array of watchers to subscribe to (the ones without
 *                  detail attached, e.g the aggregation).
 * @param watchersWithPids: the array of watchers to subscribe to, with
 *                          extra information about their processes.
 **/
function supervise(socket, watchers, watchersWithPids) {

    if (watchersWithPids == undefined) { watchersWithPids = []; }

    watchers.forEach(function(watcher) {
        addWatcher(socket, watcher);
    });

    watchersWithPids.forEach(function(watcher) {
        // If we want to get the list of processes, then we will get it
        // from the server directly
        socket.on('stats-' + watcher + '-pids', function(args) {
            // and once we know the pid, adding the watcher for it.
            args.pids.forEach(function(pid) {
                addWatcher(socket, watcher + '-' + pid);
            });
        });
    });

    // and finally ask the stats to the socket. This call happens after
    // having set the other callbacks (that's why the whole thing can look
    // a bit weird to understand
    socket.emit('get_stats', { watchers: watchers,
                               watchersWithPids: watchersWithPids});
}
