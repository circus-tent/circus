
var cpu_data;
var mem_data;

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
        });
     });

    $.getJSON('/watchers/' + name + '/stats/mem', function(data) {
       $.each(data, function(key, values) {
          for (i=0;i<values.length;i++) {
            mem_data[key].push(values[i]);
          }
        });
    });

  updateGraphs();
}

