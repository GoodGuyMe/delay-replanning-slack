project('gridbenchmark2sipp', 'cpp',
  version : '0.1',
  default_options : ['warning_level=3', 'default_library=static', 'cpp_std=c++20', 'b_ndebug=if-release'])
boost_dep = dependency('boost', static:true, modules : ['program_options', 'random', 'iostreams'])
zdep = dependency('zlib', static:true)
executable('atsipp',
           ['main.cpp', 'graph.cpp', 'segment.cpp', 'augmentedsipp.cpp', 'repeat.cpp'],
           install : true,
           dependencies : [boost_dep, zdep],
           )
