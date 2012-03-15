// JavaScript Code for Bread: A Sample Circus Client


// TODO: Be friendly to browsers that don't have WebSockets, or use socket.io
(function (globals) {
    var bread = {};

    var host = globals.location.hostname,
        port = 5000;

    var el = document.getElementsByTagName('pre')[0];

    function getSocketUrl(topic) {
        return ['ws://', host, ':', port, '/api?topic=', topic].join('');
    }

    function log(msg) {
        var args = Array.prototype.slice.call(arguments, 0),
            code = document.createElement('code');
        code.textContent = msg;
        el.appendChild(code);
    }

    bread.subscribe = function (topic) {
        var endpoint = getSocketUrl(topic),
            socket = new globals.WebSocket(endpoint);

        socket.onopen = function (e) {
            console.log('open');
            log('Listening at ' + endpoint + '...');
        };

        socket.onmessage = function (e) {
            console.log('message');
            log(e.data);
        };

        socket.onclose = function (e) {
            console.log('closed');
            log('Socket closed.');
        };
    };

    globals.bread = bread;

}(this));
