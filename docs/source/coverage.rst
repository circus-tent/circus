
Code coverage
=============


::

    Name                           Stmts   Miss  Cover   Missing
    ------------------------------------------------------------
    circus/__init__                   30     19    37%   1-13, 89-101, 107
    circus/arbiter                   204     33    84%   71-77, 84, 103-119, 182-186, 230-231, 236, 249-252, 262, 266-271, 276, 295, 311, 341
    circus/client                     52     11    79%   34-35, 39-40, 45-49, 60-61, 73
    circus/commands/addwatcher        24     14    42%   1-66, 73, 78
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
    circus/commands/restart           15     13    13%   1-56, 58-59
    circus/commands/rmwatcher         12     10    17%   1-54
    circus/commands/sendsignal        47     33    30%   1-109, 114, 118, 124, 127, 130, 138-147
    circus/commands/set               34     22    35%   1-59, 70, 75
    circus/commands/start             15     12    20%   1-53, 58
    circus/commands/stats             49     44    10%   1-89, 91-102, 109-135
    circus/commands/status            23     20    13%   1-65, 70-80
    circus/commands/stop              12      8    33%   1-50
    circus/commands/util              54     42    22%   1-38, 43, 47, 52, 55-56, 59-60, 64
    circus/config                    131     61    53%   44-47, 59, 62-65, 76-100, 119-131, 141, 152, 154, 157, 160, 163, 165, 170-199
    circus/controller                116     15    87%   75, 85-86, 94-96, 104, 116-119, 122, 145, 151, 156-157
    circus/plugins/__init__           71      9    87%   59-69, 124
    circus/plugins/flapping           64     13    80%   45-49, 61, 78, 84-91
    circus/process                   119     39    67%   3-9, 92, 97, 100-120, 133, 147, 185-186, 190, 196, 202, 208-211, 216-221, 234-235, 239
    circus/py3compat                  47     44     6%   1-38, 43-67
    circus/sighandler                 36     16    56%   34-44, 47, 50, 53, 56, 59
    circus/stats/__init__             35     23    34%   33-73, 77
    circus/stats/collector            95     77    19%   11-17, 20, 23-40, 43-65, 68, 73-75, 78, 84-90, 93-139, 142-145
    circus/stats/publisher            43     34    21%   12-22, 25-44, 47-50
    circus/stats/streamer            117     92    21%   21-39, 42, 45-47, 51-53, 57-69, 72-75, 78-82, 85-110, 113-135, 138-142
    circus/stream/__init__            35      7    80%   16, 29, 34, 37-38, 41, 68
    circus/stream/base                64     11    83%   22, 39, 51, 58-59, 64-65, 74-77
    circus/stream/sthread             19      0   100%   
    circus/util                      205    102    50%   1-55, 59-62, 68-70, 76, 90-97, 103-111, 116-117, 133-134, 144-145, 149-150, 154-157, 161-162, 168, 173, 182, 191, 204, 212, 224, 232, 234, 238-244, 250-255, 260-274, 287-288, 305, 310-311
    circus/watcher                   308     71    77%   166, 176, 223, 249, 253, 274, 278, 281-282, 287, 314, 330, 358-359, 362-363, 371, 389-391, 404-406, 416-418, 424-429, 435-436, 446-447, 483, 503-506, 513, 516, 519-521, 543, 559, 561-562, 564-565, 567-568, 570, 572-573, 577-591
    circus/web/__init__                0      0   100%   
    ------------------------------------------------------------
    TOTAL                           2305   1083    53%   


