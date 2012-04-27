
var cpu_data,
    mem_data,
    MAX_SIZE = 25;


// then updating the graphs
function updateGraphs() {
    $.each(cpu_data, function (key, val) {
        var id = '#' + key + '_cpu',
            lastid = '#' + key + '_last_cpu',
            last = val.length - 1;
        $(lastid).text(parseInt(val[last],10) + " %");
        $(id).sparkline(val, { height: '80', width: '290', fillColor: false, lineWidth: 2, lineColor: '#7AB94C', spotSize: 2, spotRadius: 4, spotColor: '#7AB94C'});
    });

    $.each(mem_data, function (key, val) {
        var id = '#' + key + '_mem',
            lastid = '#' + key + '_last_mem',
            last = val.length - 1;
        $(lastid).text(parseInt(val[last],10) + " %");
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
    $.getJSON('/watchers/' + name + '/stats/cpu?start=-3&end=-1', function (data) {
        $.each(data, function (key, values) {
            for (i=0;i<values.length;i++) {
                cpu_data[key].push(values[i]);
            }
            if (cpu_data[key].length > MAX_SIZE) {
                start = cpu_data[key].length - MAX_SIZE;
                cpu_data[key] = cpu_data[key].slice(start);
            }
        });
    });
    $.getJSON('/watchers/' + name + '/stats/mem', function (data) {
        $.each(data, function (key, values) {
            for (i=0;i<values.length;i++) {
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

$(document).ready(function() {
    $('.add_watcher').click(function() {
        $('#overlay').show();
        return false;  
    }); 
});