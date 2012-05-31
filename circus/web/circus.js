DEFAULT_CONFIG = { width: 290, height: 50, delay: 1000, dataSize: 25};

function displayGraph(id, data, config) {
    if (config == undefined) { config = DEFAULT_CONFIG; }

    var graph = d3.select('#' + id).append('svg:svg')
                                   .attr('width', '100%')
                                   .attr('height', '100%');

    var x = d3.scale.linear().domain([0, config.dataSize])
                             .range([-5, config.width + 5]);

    console.log(100, config.height);
    var y = d3.scale.linear().domain([0, 100]).range([0, config.height]);

    var line = d3.svg.line().x(function(d, i) { return x(i); })
                            .y(function(d) { return y(d); })
                            .interpolate('basis');

    graph.append('svg:path').attr('d', line(data));

    function redrawWithAnimation() {
        // change the value of the labels for last_{mem, cpu} ...
        $('#' + id + '_last_mem')
            .text(parseInt(data.mem[config.dataSize - 5]) + '%');

        $('#' + id + '_last_cpu')
            .text(parseInt(data.cpu[config.dataSize - 5]) + '%');

        // ... and redraw the graph
        graph.selectAll('path')
             .data([data.mem, data.cpu])
             .attr('transform', 'translate(' + x(1) + ')')
             .attr('d', line)
             .transition()
             .ease('linear')
             .duration(config.delay)
             .attr('transform', 'translate(' + x(0) + ')');
        console.log('updated');
    }

    setInterval(redrawWithAnimation, config.delay);
}

function zeroFilledArray(size) {
    var array = [];
    for (i = 0; i < size; i++) { array[i] = 0; }
    return array;
}

function hookData(socket, watcher, config) {
    // before starting the socket with the server, initiate the data
    // structures that will be used to store the data
    var data = { mem: zeroFilledArray(config.dataSize),
                 cpu: zeroFilledArray(config.dataSize) };

    var stream = 'stats-' + watcher;

    socket.on(stream, function(args) {
        // cap to 100
        if (args.cpu > 100) { args.cpu = 100; }
        if (args.mem > 100) { args.mem = 100; }

        // insert the new value and keep the size of the arrays
        data.cpu.shift();
        data.cpu.push(args.cpu);
        data.mem.shift();
        data.mem.push(args.mem);
    });

    return data;
}


function supervise(socket, watchers, watchersWithPids, config) {

    if (watchersWithPids == undefined) { watchersWithPids = []; }
    if (config == undefined) { config = DEFAULT_CONFIG; }

    watchers.forEach(function(watcher) {
        var data = hookData(socket, watcher, config);
        displayGraph(watcher, data, config);
    });

    watchersWithPids.forEach(function(watcher) {
        // get the list of processes for this watcher from the server
        socket.on('stats-' + watcher + '-pids', function(args) {
            args.pids.forEach(function(pid) {
                var id = watcher + '-' + pid;
                var data = hookData(socket, id);
                displayGraph(id, data, config);
            });
        });
    });

    // and finally ask the stats to the socket. This call happens after
    // having set the other callbacks (that's why the whole thing can look
    // a bit weird to understand
    socket.emit('get_stats', { watchers: watchers,
                               watchersWithPids: watchersWithPids});
}
