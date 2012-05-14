
Code coverage
=============


::

    Name                           Stmts   Miss  Cover   Missing
    ------------------------------------------------------------
    circus/__init__                   30     19    37%   1-13, 80-92, 98
    circus/arbiter                   180     35    81%   65-71, 75-90, 148-152, 187-188, 193, 204-207, 219, 223-228, 247, 263, 288-289, 293, 303-304
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
    circus/commands/rmwatcher         12     10    17%   1-54
    circus/commands/sendsignal        47     33    30%   1-109, 114, 118, 124, 127, 130, 138-147
    circus/commands/set               34     22    35%   1-59, 70, 75
    circus/commands/start             15     12    20%   1-53, 58
    circus/commands/stats             49     44    10%   1-89, 91-102, 109-135
    circus/commands/status            23     20    13%   1-65, 70-80
    circus/commands/stop              12      8    33%   1-50
    circus/commands/util              54     42    22%   1-38, 43, 47, 52, 55-56, 59-60, 64
    circus/config                    124    112    10%   11, 37-46, 50-68, 72-99, 103-205
    circus/controller                116     15    87%   75, 85-86, 94-96, 104, 116-119, 122, 145, 151, 156-157
    circus/flapping                  111     20    82%   50-60, 103-107, 131, 137-144
    circus/process                   119     40    66%   3-9, 92, 97, 100-120, 133, 147, 185-186, 190, 196, 202, 208-211, 216-221, 234-235, 239, 254
    circus/py3compat                  47     44     6%   1-38, 43-67
    circus/sighandler                 36     10    72%   39-44, 47, 50, 53, 59
    circus/stats/__init__             35     23    34%   33-73, 77
    circus/stats/collector            95     77    19%   11-17, 20, 23-40, 43-65, 68, 73-75, 78, 84-90, 93-139, 142-145
    circus/stats/publisher            43     34    21%   12-22, 25-44, 47-50
    circus/stats/streamer            117     92    21%   21-39, 42, 45-47, 51-53, 57-69, 72-75, 78-82, 85-110, 113-135, 138-142
    circus/stream/__init__            35     11    69%   16, 21-22, 25-26, 29, 34, 37-38, 41, 68
    circus/stream/base                61     10    84%   22, 39, 55-56, 61-62, 71-74
    circus/stream/sthread             19      0   100%   
    circus/util                      205    119    42%   1-55, 59-62, 68-70, 76, 90-97, 103-111, 116-117, 133-134, 144-145, 149-150, 154-157, 161-162, 168, 173, 182, 191, 204, 212, 224, 232, 234, 238-244, 250-255, 260-313
    circus/watcher                   297     72    76%   141, 207, 233, 237, 258, 262, 265-266, 271, 298, 314, 334, 342-343, 346-347, 355, 365, 383-385, 395-397, 403-408, 414-415, 425-426, 443, 462, 471, 480-483, 490, 493, 496-498, 520, 536, 538-539, 541-542, 544-545, 547, 549-550, 554-568
    circus/web/__init__                0      0   100%   
    ------------------------------------------------------------
    TOTAL                           2221   1137    49%   


