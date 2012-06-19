
Code coverage
=============


::

    Name                            Stmts   Miss  Cover   Missing
    -------------------------------------------------------------
    circus/__init__                    40     29    28%   1-35, 105-117, 123
    circus/arbiter                    185     28    85%   91-111, 132-133, 164-168, 205-206, 211, 231, 235-240, 259, 275, 305
    circus/client                      55     12    78%   18, 22, 50-51, 55-56, 61-65, 76-77
    circus/commands/addwatcher         24     14    42%   1-66, 73, 78
    circus/commands/base               72     55    24%   1-11, 19, 26, 35-79, 82, 86-97, 103-106
    circus/commands/decrproc           16     14    13%   1-53, 57-60
    circus/commands/dstats             24     23     4%   1-63, 66-81
    circus/commands/get                25     19    24%   1-66, 76, 80-86
    circus/commands/globaloptions      29     21    28%   1-73, 79-81, 93-99
    circus/commands/incrproc           20     16    20%   1-51, 58-65
    circus/commands/list               26     18    31%   1-54, 66-72
    circus/commands/numprocesses       19     17    11%   1-57, 59-60, 67-70
    circus/commands/numwatchers        14     13     7%   1-42, 45-48
    circus/commands/options            20     18    10%   1-101, 105-111
    circus/commands/quit                7      6    14%   1-36
    circus/commands/reload             17     15    12%   1-68, 70-71
    circus/commands/restart            15     13    13%   1-56, 58-59
    circus/commands/rmwatcher          12     10    17%   1-54
    circus/commands/sendsignal         49     33    33%   1-123, 133, 135, 141-143, 148, 150, 156-163
    circus/commands/set                34     22    35%   1-59, 70, 75
    circus/commands/start              15     12    20%   1-53, 58
    circus/commands/stats              49     41    16%   1-89, 93-99, 109-135
    circus/commands/status             23     20    13%   1-65, 70-80
    circus/commands/stop               12      8    33%   1-50
    circus/commands/util               58     45    22%   1-38, 43, 47, 52, 55-56, 59-60, 64, 71-73
    circus/config                     129     49    62%   42-45, 72-73, 87-90, 105-117, 128-130, 133, 144, 149, 152, 155, 157, 162-190
    circus/consumer                    32     10    69%   24, 28-31, 35, 38-42
    circus/controller                 116     16    86%   75, 85-86, 94-96, 104, 116-119, 122, 142, 145, 151, 156-157
    circus/plugins/__init__           140    101    28%   34-43, 47-55, 59-81, 85-93, 105-108, 118-119, 131, 136, 141, 149-160, 181-247, 251
    circus/process                    130     39    70%   3-9, 97, 102, 105-125, 152, 170-171, 194-195, 199, 205, 211, 217-220, 225-230, 248, 272
    circus/py3compat                   47     44     6%   1-38, 43-67
    circus/sighandler                  36     16    56%   34-44, 47, 50, 53, 56, 59
    circus/sockets                     51     12    76%   38, 50-57, 66-67, 77
    circus/stats/__init__              40     27    33%   34-81, 85
    circus/stats/client               133     99    26%   28-33, 46-117, 122-128, 131, 134-137, 141-180, 184
    circus/stats/collector             30     25    17%   8-28, 31-47
    circus/stats/publisher             26     19    27%   9-14, 17-28, 31-33
    circus/stats/streamer             130    106    18%   19-37, 41-49, 52, 55-59, 63-64, 68-81, 84-90, 93-105, 108-130, 136-160, 164-172
    circus/stream/__init__             50     14    72%   16, 29, 34, 37-38, 41, 51, 54-60, 91
    circus/stream/base                 64     11    83%   22, 39, 51, 58-59, 64-65, 74-77
    circus/stream/sthread              19      1    95%   25
    circus/util                       219    107    51%   1-56, 60-78, 84-86, 92, 106-113, 122, 125, 160-161, 165-166, 170-173, 177-178, 184-185, 190, 192, 202, 211, 224, 232, 244, 252, 254, 258-267, 273-282, 288-302, 315-316, 333, 338-339
    circus/watcher                    322     74    77%   136, 163, 173, 197, 223, 227, 237-238, 252-253, 256-257, 261, 278, 288, 304, 307-310, 338-339, 342-343, 350, 380-382, 393-398, 404-409, 415-416, 426-427, 476, 496-499, 506, 509, 512-514, 525, 551-552, 556, 559, 561-562, 564-565, 567-568, 570, 572-573, 577-582
    circus/web/__init__                 0      0   100%   
    -------------------------------------------------------------
    TOTAL                            2574   1292    50%   


