DEFAULT_CONFIG = { width: 290, height: 79, delay: 10, dataSize: 25,
                   colors: { mem: 'rgb(93, 170, 204)',
                             cpu: 'rgb(122, 185, 76)',
                             reads: 'rgb(203, 81, 58)' }};

function hookGraph(socket, watcher, metrics, prefix, capValues, config) {
    if (config == undefined) { config = DEFAULT_CONFIG; }
    if (metrics == undefined) { metrics = ['cpu', 'mem']; }
    if (prefix == undefined) { prefix = 'stats-'; }
    if (capValues == undefined) { capValues = true; }

    var series = [];
    metrics.forEach(function(metric) {
        series.push({ name: metric, color: config.colors[metric] });
    });

    var graph = new Rickshaw.Graph({
            element: document.getElementById(watcher),
            min: 0,
            max: 100,
            width: config.width,
            height: config.height,
            renderer: 'line',
            interpolation: 'basis',
            series: new Rickshaw.Series.FixedDuration(
                series, undefined,
                { timeInterval: config.delay,
                  maxDataPoints: 25,
                  timeBase: new Date().getTime() / 1000 })
    });

    socket.on(prefix + watcher, function(received) {
        var data = {};

        // cap to 100
        metrics.forEach(function(metric) {
            if (received[metric] > 100) {
                data[metric] = 100;
            } else {
                data[metric] = received[metric];
            }

            var value = data[metric].toFixed(1);
            if (metric != 'reads') { value += '%'; }

            $('#' + watcher + '_last_' + metric).text(value);
        });

	if(received.hasOwnProperty("age")){
	    var val =  '(' + Math.round(received['age']) + 's)';
            $('#' + watcher + '_last_age').text(val);
	}

        graph.series.addData(data);
        graph.render();
    });
}


function supervise(socket, watchers, watchersWithPids, config) {

    if (watchersWithPids == undefined) { watchersWithPids = []; }
    if (config == undefined) { config = DEFAULT_CONFIG; }

    watchers.forEach(function(watcher) {
        // only the aggregation is sent here
        if (watcher == 'sockets') {
            hookGraph(socket, 'socket-stats', ['reads'], '', false, config);
        } else {
            hookGraph(socket, watcher, ['cpu', 'mem'], 'stats-', true, config);
        }
    });

    watchersWithPids.forEach(function(watcher) {
        if (watcher == 'sockets') {
            socket.on('socket-stats-fds', function(data) {
                data.fds.forEach(function(fd) {
                    hookGraph(socket, 'socket-stats-' + fd, ['reads'],
                              '', false, config);
                });
            });
        } else {
            // get the list of processes for this watcher from the server
            socket.on('stats-' + watcher + '-pids', function(data) {
                data.pids.forEach(function(pid) {
                    var id = watcher + '-' + pid;
                    hookGraph(socket, id, ['cpu', 'mem'], 'stats-', false,
                              config);
                });
            });
        }
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

    $('a.stopped, a.active').click(function(e) {
        return confirm('Are you sure you want to change the status ?');
    });

});
