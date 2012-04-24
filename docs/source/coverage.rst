
Code coverage
=============


::

    Name                           Stmts   Miss  Cover   Missing
    ------------------------------------------------------------
    circus/__init__                   30     19    37%   1-13, 80-92, 98
    circus/arbiter                   139     24    83%   60-74, 125-129, 153-156, 168, 172-177, 196, 212, 236-237, 241
    circus/client                     50     11    78%   34-35, 39-40, 45-49, 60-61, 69
    circus/commands/addwatcher        16     15     6%   1-67
    circus/commands/base              72     55    24%   1-11, 19, 26, 35-79, 82, 86-97, 103-106
    circus/commands/decrproc          16     14    13%   1-53, 57-60
    circus/commands/get               25     19    24%   1-66, 76, 80-86
    circus/commands/incrproc          16     14    13%   1-51, 55-58
    circus/commands/list              23     17    26%   1-52, 61-67
    circus/commands/numprocesses      19     17    11%   1-57, 59-60, 67-70
    circus/commands/numwatchers       14     13     7%   1-42, 45-48
    circus/commands/options           20     18    10%   1-100, 104-110
    circus/commands/quit               7      6    14%   1-36
    circus/commands/reload            17     15    12%   1-68, 70-71
    circus/commands/rmwatcher         11     10     9%   1-54
    circus/commands/sendsignal        47     33    30%   1-109, 114, 118, 124, 127, 130, 138-147
    circus/commands/set               83     62    25%   1-74, 79, 83, 87-88, 91-92, 95-96, 100, 106-123, 134
    circus/commands/start             15     12    20%   1-53, 58
    circus/commands/stats             49     44    10%   1-89, 91-102, 109-135
    circus/commands/status            23     20    13%   1-65, 70-80
    circus/commands/stop              12      8    33%   1-50
    circus/config                    121    109    10%   10, 35-44, 48-66, 70-97, 101-200
    circus/controller                113     15    87%   75, 85-86, 93-95, 103, 115-118, 121, 141, 147, 152-153
    circus/flapping                  109     20    82%   50-60, 101-105, 129, 135-142
    circus/process                   118     37    69%   3-9, 92, 97, 100-120, 133, 184-185, 189, 195, 201, 207-210, 215-220, 238, 253
    circus/py3compat                  47     44     6%   1-38, 43-67
    circus/sighandler                 36     16    56%   34-44, 47, 50, 53, 56, 59
    circus/stream/__init__            35     11    69%   16, 21-22, 25-26, 29, 34, 37-38, 41, 68
    circus/stream/base                61     10    84%   22, 39, 55-56, 61-62, 71-74
    circus/stream/sthread             19      0   100%   
    circus/util                      193    110    43%   1-54, 58-61, 67-69, 75, 89-92, 96-97, 113-114, 124-125, 129-130, 134-137, 141-142, 149, 158, 167, 180, 188, 200, 208, 210, 214-220, 226-231, 236-289
    circus/watcher                   269     67    75%   133, 196, 218, 224, 249, 265, 285, 292-293, 296-297, 305, 315, 331-333, 343-345, 351-356, 362-363, 373-374, 391, 410, 419, 428-431, 438, 441, 444-446, 468, 484, 486-487, 489-490, 492-493, 495, 497-498, 502-516
    circus/web/__init__                0      0   100%   
    ------------------------------------------------------------
    TOTAL                           1825    885    52%   


