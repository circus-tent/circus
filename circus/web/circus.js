DEFAULT_CONFIG = { width: 290, height: 79, delay: 10, dataSize: 25,
                   memory_color: 'rgb(93, 170, 204)',
                   cpu_color: 'rgb(122, 185, 76)'};

function hookGraph(socket, watcher, config) {
    if (config == undefined) { config = DEFAULT_CONFIG; }

    var graph = new Rickshaw.Graph({
            element: document.getElementById(watcher),
            width: config.width,
            height: config.height,
            renderer: 'line',
            interpolation: 'basis',
            series: new Rickshaw.Series.FixedDuration(
                [{ name: 'mem', color: config.memory_color },
                 { name: 'cpu', color: config.cpu_color }],
                undefined,
                { timeInterval: config.delay,
                  maxDataPoints: 25,
                  timeBase: new Date().getTime() / 1000 })
    });

    socket.on('stats-' + watcher, function(data) {
        // cap to 100
        if (data.cpu > 100) { data.cpu = 100; }
        if (data.mem > 100) { data.mem = 100; }

        $('#' + watcher + '_last_mem').text(parseInt(data.mem) + '%');
        $('#' + watcher + '_last_cpu').text(parseInt(data.cpu) + '%');

        graph.series.addData(data);
        graph.render();
    });
}


function supervise(socket, watchers, watchersWithPids, config) {

    if (watchersWithPids == undefined) { watchersWithPids = []; }
    if (config == undefined) { config = DEFAULT_CONFIG; }

    watchers.forEach(function(watcher) {
        hookGraph(socket, watcher, config);
    });

    watchersWithPids.forEach(function(watcher) {
        // get the list of processes for this watcher from the server
        socket.on('stats-' + watcher + '-pids', function(data) {
            data.pids.forEach(function(pid) {
                var id = watcher + '-' + pid;
                hookGraph(socket, id, config);
            });
        });
    });

    // start the streaming of data, once the callbacks in place.
    socket.emit('get_stats', { watchers: watchers,
                               watchersWithPids: watchersWithPids});
}

$(document).ready(function() {
    $('.add_watcher').click(function() {
        $('#overlay').show();
        return false;
    });

    $('#cancel_watcher_btn').click(function() {
        $('#overlay').hide();
        return false;
    });

    $('#cancel_watcher_btn').click(function () {
        $('#overlay').hide();
        return false;
    });

    $('a.stopped, a.active').click(function(e) {
        return confirm("Are you sure you want to change the status ?");
    });

});
