
Code coverage
=============


::

    Name                                                              Stmts   Miss  Cover   Missing
    -----------------------------------------------------------------------------------------------
    /Users/tarek/Dev/github.com/circus/circus/__init__                   24     14    42%   1-20, 69
    /Users/tarek/Dev/github.com/circus/circus/arbiter                   129     29    78%   88-108, 124-127, 139, 143-148, 167, 182, 206-207, 213
    /Users/tarek/Dev/github.com/circus/circus/client                     49     17    65%   36-37, 41-42, 47-59, 61-63, 71
    /Users/tarek/Dev/github.com/circus/circus/commands/addwatcher        16     15     6%   1-65
    /Users/tarek/Dev/github.com/circus/circus/commands/base              72     55    24%   1-11, 19, 26, 35-79, 82, 86-97, 103-106
    /Users/tarek/Dev/github.com/circus/circus/commands/decrproc          16     14    13%   1-53, 57-60
    /Users/tarek/Dev/github.com/circus/circus/commands/get               25     19    24%   1-66, 76, 80-86
    /Users/tarek/Dev/github.com/circus/circus/commands/incrproc          16     14    13%   1-51, 55-58
    /Users/tarek/Dev/github.com/circus/circus/commands/list              23     17    26%   1-52, 61-67
    /Users/tarek/Dev/github.com/circus/circus/commands/numprocesses      19     17    11%   1-57, 59-60, 67-70
    /Users/tarek/Dev/github.com/circus/circus/commands/numwatchers       14     13     7%   1-42, 45-48
    /Users/tarek/Dev/github.com/circus/circus/commands/options           20     18    10%   1-98, 102-108
    /Users/tarek/Dev/github.com/circus/circus/commands/quit               9      8    11%   1-47
    /Users/tarek/Dev/github.com/circus/circus/commands/reload            17     15    12%   1-68, 70-71
    /Users/tarek/Dev/github.com/circus/circus/commands/rmwatcher         13     12     8%   1-59
    /Users/tarek/Dev/github.com/circus/circus/commands/sendsignal        47     33    30%   1-109, 114, 118, 124, 127, 130, 138-147
    /Users/tarek/Dev/github.com/circus/circus/commands/set               83     62    25%   1-74, 78, 82, 85-86, 89-90, 93-94, 98, 104-121, 132
    /Users/tarek/Dev/github.com/circus/circus/commands/start             15     12    20%   1-53, 58
    /Users/tarek/Dev/github.com/circus/circus/commands/stats             49     44    10%   1-89, 91-102, 109-135
    /Users/tarek/Dev/github.com/circus/circus/commands/status            23     20    13%   1-65, 70-80
    /Users/tarek/Dev/github.com/circus/circus/commands/stop              14     10    29%   1-57
    /Users/tarek/Dev/github.com/circus/circus/controller                113     14    88%   85-86, 93-95, 103, 115-118, 121, 141, 147, 152-153
    /Users/tarek/Dev/github.com/circus/circus/flapping                  109     19    83%   50-51, 54, 56, 62-65, 89, 102-105, 134-143
    /Users/tarek/Dev/github.com/circus/circus/process                   117     37    68%   3-9, 91, 96, 99-119, 132, 184-185, 189, 195, 201, 207-210, 215-220, 238, 253
    /Users/tarek/Dev/github.com/circus/circus/sighandler                 36     16    56%   34-44, 47, 50, 53, 56, 59
    /Users/tarek/Dev/github.com/circus/circus/stream                    106     30    72%   16, 21-22, 25-26, 29, 45, 61, 76-77, 92-95, 115-135
    /Users/tarek/Dev/github.com/circus/circus/tests/__init__              0      0   100%   
    /Users/tarek/Dev/github.com/circus/circus/tests/support              71      9    87%   24, 31-34, 37-39, 81
    /Users/tarek/Dev/github.com/circus/circus/tests/test_arbiter        130     62    52%   13-19, 22-23, 26-27, 30, 33-36, 40-42, 51, 60, 65, 70-76, 80, 93, 98-99, 104-105, 110-111, 116-119, 123-124, 128, 133-142, 147-157, 161, 165-166, 170-171
    /Users/tarek/Dev/github.com/circus/circus/tests/test_client          45     15    67%   8-12, 19-24, 28, 32, 36, 40, 43, 46, 58
    /Users/tarek/Dev/github.com/circus/circus/tests/test_process         37     10    73%   49-56, 59-62
    /Users/tarek/Dev/github.com/circus/circus/tests/test_runner          13      7    46%   6-8, 15-21
    /Users/tarek/Dev/github.com/circus/circus/tests/test_sighandler      40     28    30%   8-15, 18-19, 22-25, 28-29, 32-35, 39-41, 49-60
    /Users/tarek/Dev/github.com/circus/circus/tests/test_util            63      4    94%   81-84
    /Users/tarek/Dev/github.com/circus/circus/tests/test_watcher         52     11    79%   12-19, 30, 38, 77
    /Users/tarek/Dev/github.com/circus/circus/util                      188     89    53%   1-32, 38-40, 46, 60-63, 67-68, 84, 95-96, 100-101, 105, 107-108, 112-113, 129, 138, 159, 171, 179, 181, 187-191, 199, 207-210, 213-257, 261-263, 268, 271-282
    /Users/tarek/Dev/github.com/circus/circus/watcher                   272     70    74%   100, 135, 157, 163, 188, 204, 224, 231-232, 235-236, 244, 254, 270-272, 282-284, 290-295, 301-302, 308, 312-313, 342-344, 357, 366, 375-378, 385, 388, 399, 405, 415, 431, 433-434, 436-437, 439-440, 442, 444-445, 449-463, 475
    /Users/tarek/Dev/github.com/gevent-zeromq/gevent_zeromq/core        120     35    71%   3-15, 35-54, 57, 72, 78, 92-95, 99, 102, 109, 114-116, 125, 135, 147-151, 161, 168, 172, 195, 199
    -----------------------------------------------------------------------------------------------
    TOTAL                                                              2205    914    59%   


