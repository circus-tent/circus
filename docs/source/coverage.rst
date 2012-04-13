
Code coverage
=============


::

    Name                                                              Stmts   Miss  Cover   Missing
    -----------------------------------------------------------------------------------------------
    /Users/tarek/Dev/github.com/circus/circus/__init__                   24     14    42%   1-20, 62
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
    /Users/tarek/Dev/github.com/circus/circus/controller                113     15    87%   75, 85-86, 93-95, 103, 115-118, 121, 141, 147, 152-153
    /Users/tarek/Dev/github.com/circus/circus/flapping                  109     17    84%   50-51, 54, 56, 62-65, 89, 102-105, 138-143
    /Users/tarek/Dev/github.com/circus/circus/process                   146     44    70%   3-9, 115, 120, 123-143, 156, 179-180, 202, 205-207, 250-251, 255, 261, 267, 273-276, 281-286, 304, 314, 319
    /Users/tarek/Dev/github.com/circus/circus/sighandler                 36     16    56%   34-44, 47, 50, 53, 56, 59
    /Users/tarek/Dev/github.com/circus/circus/stream                     43     14    67%   18-19, 22-23, 26, 46, 50-51, 60-64, 67
    /Users/tarek/Dev/github.com/circus/circus/tests/__init__              0      0   100%   
    /Users/tarek/Dev/github.com/circus/circus/tests/support              61     12    80%   24, 31-34, 37-39, 69-72
    /Users/tarek/Dev/github.com/circus/circus/tests/test_arbiter        130     62    52%   13-19, 22-23, 26-27, 30, 33-36, 40-42, 51, 60, 65, 70-76, 80, 93, 98-99, 104-105, 110-111, 116-119, 123-124, 128, 133-142, 147-157, 161, 165-166, 170-171
    /Users/tarek/Dev/github.com/circus/circus/tests/test_client          45     15    67%   8-12, 19-24, 28, 32, 36, 40, 43, 46, 58
    /Users/tarek/Dev/github.com/circus/circus/tests/test_process         68     14    79%   84-91, 94-97, 102-103, 115-118
    /Users/tarek/Dev/github.com/circus/circus/tests/test_runner          13      7    46%   6-8, 15-21
    /Users/tarek/Dev/github.com/circus/circus/tests/test_sighandler      40     28    30%   8-15, 18-19, 22-25, 28-29, 32-35, 39-41, 49-60
    /Users/tarek/Dev/github.com/circus/circus/tests/test_util            63      4    94%   81-84
    /Users/tarek/Dev/github.com/circus/circus/tests/test_watcher         42      8    81%   9-13, 22, 30, 56
    /Users/tarek/Dev/github.com/circus/circus/util                      164     75    54%   1-31, 37-39, 45, 59, 66-67, 83-84, 94-95, 99-100, 104-105, 107, 112, 128, 137, 150, 158, 170, 178, 180, 187-190, 196-201, 206-238
    /Users/tarek/Dev/github.com/circus/circus/watcher                   249     71    71%   73, 95, 101, 126, 142, 160-161, 164-165, 173, 192-194, 204-206, 212-217, 223-224, 230, 234-235, 258-260, 272, 284-287, 294, 297, 300-302, 306-308, 314, 324, 340, 342-343, 345-346, 348-349, 351, 353-354, 358-372, 384
    /Users/tarek/Dev/github.com/gevent-zeromq/gevent_zeromq/core        120     40    67%   3-15, 35-54, 57, 78, 81-83, 91-95, 99, 102, 109-116, 125, 135, 147-151, 161, 168, 172, 195, 199
    -----------------------------------------------------------------------------------------------
    TOTAL                                                              2135    900    58%   


