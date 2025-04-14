#include "atf.hpp"
#include "augmentedsipp.hpp"
#include "repeat.hpp"

double update_reference_time(const EdgeATF& path, rePEAT::Open open_list){
    double upper_bound = path.beta;
    double lower_bound = path.alpha;
    std::cout << "Starting update tref with alpha " << lower_bound << " beta " << upper_bound << " delta " << path.delta << std::endl;
    return upper_bound;
}

CompoundATF<std::vector<GraphNode *>> rePEAT::search(GraphNode * source, const Location& dest, MetaData & m,
                                                     double start_time, gamma_t gamma){
    double t_ref = start_time;
    std::vector<GraphNode *> path;
    CompoundATF solutions(path);
    m.init();
    while(t_ref < end(source->state.interval)){
        std::cout << "tref: " << t_ref << "\n";
        Open open_list;
        open_list.emplace(EdgeATF(-std::numeric_limits<double>::infinity(), t_ref, std::numeric_limits<double>::infinity(), 0.0, gamma), 0, source, nullptr,
                          -1, nullptr);
        auto res = asipp::search_core(open_list, dest, m);
        if(res.first.size() == 0){
            break;
        }
        solutions.add(res.second, res.first);
        t_ref = update_reference_time(res.second, open_list);
    }
    return solutions;
}