
var cpu_data;
var mem_data;
var MAX_SIZE = 25;


// then updating the graphs
function updateGraphs() {

$.each(cpu_data, function(key, val) {
  var id = '#' + key + '_cpu';
  var lastid = '#' + key + '_last_cpu';
  var last = val.length - 1;
  $(lastid).text(val[last] + " %");
  $(id).sparkline(val, {width: '55%'});
});

$.each(mem_data, function(key, val) {
  var id = '#' + key + '_mem';
  var lastid = '#' + key + '_last_mem';
  var last = val.length - 1;
  $(lastid).text(val[last] + " %");
  $(id).sparkline(val, {width: '55%'});
});
}

// first run: getting all the data
function initializeGraphs(name) {
    $.getJSON('/watchers/' + name + '/stats/cpu', function(data) {
        cpu_data = data;
    });
    $.getJSON('/watchers/' + name + '/stats/mem', function(data) {
        mem_data = data;
    });
    updateGraphs();
}


function refreshData(name) {

    $.getJSON('/watchers/' + name + '/stats/cpu?start=-3&end=-1', function(data) {
       $.each(data, function(key, values) {
          for (i=0;i<values.length;i++) {
            cpu_data[key].push(values[i]);
        }
        if (cpu_data[key].length > MAX_SIZE) {
              start = cpu_data[key].length - MAX_SIZE;
              cpu_data[key] = cpu_data[key].slice(start);
           }
        });
     });

    $.getJSON('/watchers/' + name + '/stats/mem', function(data) {
       $.each(data, function(key, values) {
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
  $(id).sparkline(circusd_cpu_data, {width: '55%'});
  var id = '#circusd_mem';
  var lastid = '#circusd_last_mem';
  var last = circusd_mem_data.length - 1;
  $(lastid).text(circusd_mem_data[last] + " %");
  $(id).sparkline(circusd_mem_data, {width: '55%'});
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

    $.getJSON('/circusd/stats/cpu?start=-3&end=-1', function(data) {
        var values = data['info'];
        for (i=0;i<values.length;i++) {
            circusd_cpu_data.push(values[i]);
        }
        if (circusd_cpu_data.length > MAX_SIZE) {
              start = circusd_cpu_data.length - MAX_SIZE;
              circusd_cpu_data = circusd_cpu_data.slice(start);
        }
     });

    
    $.getJSON('/circusd/stats/mem?start=-3&end=-1', function(data) {
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

