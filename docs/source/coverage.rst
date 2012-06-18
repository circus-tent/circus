
Code coverage
=============


::

    Name                            Stmts   Miss  Cover   Missing
    -------------------------------------------------------------
    circus/__init__                    40     29    28%   1-35, 105-117, 123
    circus/arbiter                    185     28    85%   91-111, 132-133, 164-168, 204-205, 210, 230, 234-239, 258, 274, 304
    circus/client                      55     12    78%   18, 22, 50-51, 55-56, 61-65, 76-77
    circus/commands/addwatcher         24     14    42%   1-66, 73, 78
    circus/commands/base               72     55    24%   1-11, 19, 26, 35-79, 82, 86-97, 103-106
    circus/commands/decrproc           16     14    13%   1-53, 57-60
    circus/commands/dstats             24     23     4%   1-63, 66-81
    circus/commands/get                25     19    24%   1-66, 76, 80-86
    circus/commands/globaloptions      29     21    28%   1-73, 79-81, 93-99
    circus/commands/incrproc           20     16    20%   1-51, 58-65
    circus/commands/list               23     17    26%   1-52, 61-67
    circus/commands/listpids           17     13    24%   1-41, 47-50
    circus/commands/numprocesses       19     17    11%   1-57, 59-60, 67-70
    circus/commands/numwatchers        14     13     7%   1-42, 45-48
    circus/commands/options            20     18    10%   1-101, 105-111
    circus/commands/quit                7      6    14%   1-36
    circus/commands/reload             17     15    12%   1-68, 70-71
    circus/commands/restart            15     13    13%   1-56, 58-59
    circus/commands/rmwatcher          12     10    17%   1-54
    circus/commands/set                34     22    35%   1-59, 70, 75
    circus/commands/start              15     12    20%   1-53, 58
    circus/commands/stats              49     41    16%   1-89, 93-99, 109-135
    circus/commands/status             23     20    13%   1-65, 70-80
    circus/commands/stop               12      8    33%   1-50
    circus/commands/util               54     42    22%   1-38, 43, 47, 52, 55-56, 59-60, 64
    circus/config                     147     60    59%   41-44, 71-72, 89-113, 118-121, 136-148, 159-161, 164, 175, 180, 183, 186, 188, 193-218
    circus/consumer                    32     10    69%   24, 28-31, 35, 38-42
    circus/controller                 116     16    86%   75, 85-86, 94-96, 104, 116-119, 122, 142, 145, 151, 156-157
    circus/plugins/__init__           140    101    28%   34-43, 47-55, 59-81, 85-93, 105-108, 118-119, 131, 136, 141, 149-160, 181-247, 251
    circus/process                    123     40    67%   3-9, 97, 102, 105-125, 152, 169-170, 193-194, 198, 204, 210, 216-219, 224-229, 242-243, 247
    circus/py3compat                   47     44     6%   1-38, 43-67
    circus/sighandler                  36     16    56%   34-44, 47, 50, 53, 56, 59
    circus/sockets                     51     12    76%   38, 50-57, 66-67, 77
    circus/stats/__init__              40     27    33%   34-81, 85
    circus/stats/client               133     99    26%   28-33, 46-117, 122-128, 131, 134-137, 141-180, 184
    circus/stats/collector             30     25    17%   8-28, 31-47
    circus/stats/publisher             26     19    27%   9-14, 17-28, 31-33
    circus/stats/streamer             130    106    18%   19-37, 41-49, 52, 55-59, 63-64, 68-81, 84-90, 93-105, 108-130, 136-160, 164-172
    circus/stream/__init__             35      7    80%   16, 29, 34, 37-38, 41, 68
    circus/stream/base                 64     11    83%   22, 39, 51, 58-59, 64-65, 74-77
    circus/stream/sthread              19      1    95%   25
    circus/util                       216    112    48%   1-56, 60-78, 84-86, 92, 106-113, 122, 125, 134-135, 139-140, 144-145, 153-154, 160-161, 165-166, 170-173, 177-178, 184-185, 190, 192, 202, 211, 224, 232, 244, 252, 254, 258-264, 270-275, 280-294, 307-308, 325, 330-331
    circus/watcher                    327     76    77%   136, 164, 174, 233, 252, 259, 263, 284, 288, 291-292, 297, 324, 340, 343-346, 375-376, 379-380, 388, 406-408, 421-423, 427, 430-435, 441-446, 452-453, 463-464, 500, 520-523, 530, 533, 536-538, 549, 563, 578-579, 583, 586, 588-589, 591-592, 594-595, 597, 599-600, 604-609
    circus/web/__init__                 0      0   100%   
    circus/web/circushttpd            158    151     4%   7-12, 19-325
    -------------------------------------------------------------
    TOTAL                            2691   1431    47%   


