import datetime


def stream_log(stream_out, data):
    """Timestamp the line with the current time."""
    for d in data.split('\n'):
        stream_out.write(datetime.now().strftime('%Y-%m-%dT%H:%M:%S\t'))
        stream_out.write(d)
        stream_out.write('\n')
