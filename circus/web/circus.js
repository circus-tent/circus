var data = {},
    watchers = [],
    MAX_SIZE = 25,
    CPU_OPTIONS = {height: '50', width: '200', fillColor: false, lineWidth: 2, lineColor: '#7AB94C', spotSize: 2, spotRadius: 4, spotColor: '#7AB94C'},
    MEM_OPTIONS = {composite: true, height: '50', width: '200', fillColor: false, lineWidth: 2, lineColor: '#5DAACC', spotSize: 2, spotRadius: 4, spotColor: '#5DAACC'};


function addWatcher(socket, watcher, aggregate){
    if (aggregate === undefined){
       aggregate = false;
    }

    // before starting the socket with the server, initiate the data structures
    // that will be used to store the data
    data[watcher] = {mem:[], cpu:[]};

    // tell the server that we want to get stats about the watchers.
    // it will answer on some specific channels that are named
    // "stats-<watcher>", so we need to register to them.
    socket.emit('stats', {streams: watchers, aggregate: aggregate});

    socket.on('stats-' + watcher, function (args) {
        data[watcher]['cpu'].push(args['cpu']);
        data[watcher]['mem'].push(args['mem']);
    });

    // add the watcher to the list of watchers. this is useful when
    // refreshing graphs (because we want to refresh them all at once)
    watchers.push(watcher);
}

function displayGraph(watcher, metric, width, height, updateDelay){

    var id = "#" + watcher;
    var graph = d3.select(id).append("svg:svg").attr("width", "100%").attr("height", "100%");

    var x = d3.scale.linear().domain([0, 48]).range([-5, width]);
    var y = d3.scale.linear().domain([0, 10]).range([0, height]);

    // create a line object that represents the SVN line we're creating
    var line = d3.svg.line()
               .x(function(d,i) { return x(i); })
               .y(function(d) { return y(d); })
               .interpolate("basis")

    // display the line by appending an svg:path element with the data line
    graph.append("svg:path").attr("d", line(data[watcher][metric]));

    function redrawWithAnimation() {
        console.log('redrawing ' + watcher);
        // update with animation
        graph.selectAll("path")
        .data(data[watcher][metric])
        .attr("transform", "translate(" + x(1) + ")")
        .attr("d", line)
        .transition()
        .ease("linear")
        .duration(updateDelay)
        .attr("transform", "translate(" + x(0) + ")");
    }

    setInterval(redrawWithAnimation, updateDelay);
}

/**
 * Update the graphs accordingly to the data that is in memory.
 *
 * @param worker the name of the worker to update
 **/
function updateGraph(worker){
    console.log("updating " + worker);
    // before updating the graphs, slice the data to lower the memory print.
    ['mem', 'cpu'].forEach(function(val){
        if (data[worker][val].length > MAX_SIZE){
            start = data[worker][val].length - MAX_SIZE;
            data[worker][val] = data[worker][val].slice(start);
        }
    });

    // Each watcher is named "#<worker> and there also are some special ids for
    // the last mem and cpu usages.
    var id = "#" + worker;
    var lastid_cpu = id + "_last_cpu";
    var lastid_mem = id + "_last_mem";
    var cpu = data[worker]['cpu'];
    var mem = data[worker]['mem'];

    // update the sparklines
    $(id).sparkline(cpu, CPU_OPTIONS);
    $(id).sparkline(mem, MEM_OPTIONS);

    // and the numbers displayed
    $(id + "_last_cpu").text(parseInt(cpu[cpu.length - 1], 10) + " %");
    $(id + "_last_mem").text(parseInt(mem[mem.length - 1], 10) + " %");
}

/**
 * Update all the graphs that are registered in the "watchers" variable.
 **/
function updateGraphs(){
    for (i=0; i < watchers.length; i++){
        updateGraph(watchers[i]);
    }
}
