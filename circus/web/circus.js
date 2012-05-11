
var cpu_data,
    mem_data,
    MAX_SIZE = 25;


// then updating the graphs
function updateGraphs() {
    $.each(cpu_data, function (key, val) {
        var id = '#' + key + '_cpu',
        lastid = '#' + key + '_last_cpu',
        last = val.length - 1;
        $(lastid).text(parseInt(val[last], 10) + " %");
        $(id).sparkline(val, { height: '80', width: '290', fillColor: false, lineWidth: 2, lineColor: '#7AB94C', spotSize: 2, spotRadius: 4, spotColor: '#7AB94C'});
    });

    $.each(mem_data, function (key, val) {
        var id = '#' + key + '_mem',
            lastid = '#' + key + '_last_mem',
            last = val.length - 1;
        $(lastid).text(parseInt(val[last], 10) + " %");
        $('#' + key + '_cpu').sparkline(val, {composite: true, height: '80', width: '290', fillColor: false, lineWidth: 2, lineColor: '#5DAACC', spotSize: 2, spotRadius: 4, spotColor: '#5DAACC'});
    });

}

// first run: getting all the data
function initializeGraphs(name) {
    $.getJSON('/watchers/' + name + '/stats/cpu', function (data) {
        cpu_data = data;
    });
    $.getJSON('/watchers/' + name + '/stats/mem', function (data) {
        mem_data = data;
    });
    updateGraphs();
}

function refreshData(name) {
    var i = 0;
    $.getJSON('/watchers/' + name + '/stats/cpu?start=-10&end=-1', function (data) {
        $.each(data, function (key, values) {
            for (i = 0; i < values.length; i++) {
                cpu_data[key].push(values[i]);
            }
            if (cpu_data[key].length > MAX_SIZE) {
                start = cpu_data[key].length - MAX_SIZE;
                cpu_data[key] = cpu_data[key].slice(start);
            }
        });
    });
    $.getJSON('/watchers/' + name + '/stats/mem?start=-10&end=-1', function (data) {
        $.each(data, function (key, values) {
            for (i = 0; i < values.length; i++) {
                mem_data[key].push(values[i]);
            }
            if (mem_data[key].length > MAX_SIZE) {
                start = mem_data[key].length - MAX_SIZE;
                mem_data[key] = mem_data[key].slice(start);
            }
        });
    });
    updateGraphs();
}

/*
* Circusd graph
*/
var circusd_cpu_data,
    circusd_mem_data;

function updateCircusdGraph() {

    var id = '#circusd',
        lastid_cpu = '#circusd_last_cpu',
        last_cpu = circusd_cpu_data.length - 1,
        lastid_mem = '#circusd_last_mem',
        last_mem = circusd_mem_data.length - 1;

    $(lastid_cpu).text(circusd_cpu_data[last_cpu] + " %");
    $(id).sparkline(circusd_cpu_data, { height: '50', width: '200', fillColor: false, lineWidth: 2, lineColor: '#7AB94C', spotSize: 2, spotRadius: 4, spotColor: '#7AB94C'});
    $(lastid_mem).text(circusd_mem_data[last_mem] + " %");
    $(id).sparkline(circusd_mem_data, {composite: true, height: '50', width: '200', fillColor: false, lineWidth: 2, lineColor: '#5DAACC', spotSize: 2, spotRadius: 4, spotColor: '#5DAACC'});
}

function initializeCircusdGraph() {
    $.getJSON('/circusd/stats/cpu', function (data) {
        circusd_cpu_data = data['info'];
    });
    $.getJSON('/circusd/stats/mem', function (data) {
        circusd_mem_data = data['info'];
    });
    updateCircusdGraph();
}

function refreshCircusdGraph() {
    var start = 0;
    $.getJSON('/circusd/stats/cpu?start=-3&end=-1', function (data) {
        var values = data['info'];
        for (i = 0;i<values.length;i++) {
            circusd_cpu_data.push(values[i]);
        }
        if (circusd_cpu_data.length > MAX_SIZE) {
            start = circusd_cpu_data.length - MAX_SIZE;
            circusd_cpu_data = circusd_cpu_data.slice(start);
        }
    });

    $.getJSON('/circusd/stats/mem?start=-3&end=-1', function (data) {
        var values = data['info'];

        for (i = 0;i<values.length;i++) {
            circusd_mem_data.push(values[i]);
        }
        if (circusd_mem_data.length > MAX_SIZE) {
            start = circusd_mem_data.length - MAX_SIZE;
            circusd_mem_data = circusd_mem_data.slice(start);
        }
    });

    updateCircusdGraph();
}


/*
* Circusd graph
*/
var circusd_cpu_data;
var circusd_mem_data;

function updateCircusdGraph() {
  var id = '#circusd_cpu';
  var lastid = '#circusd_last_cpu';
  var last = circusd_cpu_data.length - 1;
  $(lastid).text(circusd_cpu_data[last] + " %");
  $(id).sparkline(circusd_cpu_data, { height: '80', width: '290', fillColor: false, lineWidth: 2, lineColor: '#7AB94C', spotSize: 2, spotRadius: 4, spotColor: '#7AB94C'});
  //var id = '#circusd_mem';
  var lastid = '#circusd_last_mem';
  var last = circusd_mem_data.length - 1;
  $(lastid).text(circusd_mem_data[last] + " %");
  $(id).sparkline(circusd_mem_data, {composite: true, height: '80', width: '290', fillColor: false, lineWidth: 2, lineColor: '#5DAACC', spotSize: 2, spotRadius: 4, spotColor: '#5DAACC'});
}

function initializeCircusdGraph() {
    $.getJSON('/circusd/stats/cpu', function(data) {
        circusd_cpu_data = data['info'];
    });
    $.getJSON('/circusd/stats/mem', function(data) {
        circusd_mem_data = data['info'];
    });
    updateCircusdGraph();
}


function refreshCircusdGraph() {

    $.getJSON('/circusd/stats/cpu?start=-10&end=-1', function(data) {
        var values = data['info'];
        for (i=0;i<values.length;i++) {
            circusd_cpu_data.push(values[i]);
        }
        if (circusd_cpu_data.length > MAX_SIZE) {
              start = circusd_cpu_data.length - MAX_SIZE;
              circusd_cpu_data = circusd_cpu_data.slice(start);
        }
     });


    $.getJSON('/circusd/stats/mem?start=-10&end=-1', function(data) {
        var values = data['info'];

        for (i=0;i<values.length;i++) {
            circusd_mem_data.push(values[i]);
        }
        if (circusd_mem_data.length > MAX_SIZE) {
              start = circusd_mem_data.length - MAX_SIZE;
              circusd_mem_data = circusd_mem_data.slice(start);
        }
     });

  updateCircusdGraph();
}

$(document).ready(function () {
    $('.add_watcher').click(function () {
        $('#overlay').show();
        return false;
    });
});
