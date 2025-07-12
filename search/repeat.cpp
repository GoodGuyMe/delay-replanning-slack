#include "atf.hpp"
#include "augmentedsipp.hpp"
#include "repeat.hpp"

//double update_reference_time(const EdgeATF& path, rePEAT::Open& open_list){
//    intervalTime_t upper_bound = path.beta;
//    intervalTime_t lower_bound = path.alpha;
////    std::cerr << "Starting update tref with alpha " << lower_bound << " beta " << upper_bound << " delta " << path.delta << " gamma [";
////    for (gam_item_t gamma : path.gamma) {
////        std::cerr << "<" << gamma.first << ", " << gamma.second << ">, ";
////    }
////    std::cerr << "]\n";
////    std::cerr << "Queue has " << open_list.size() << " elements." << std::endl;
//    while(lower_bound < upper_bound){
//        if(open_list.empty()){
//            return std::numeric_limits<double>::infinity();
//        }
//        auto n = open_list.top();
//        open_list.pop();
////        std::cerr << "popped " << n << std::endl;
//        lower_bound = n.g.alpha;
////        std::cerr << "new lb " << lower_bound << std::endl;
//        if (lower_bound > path.alpha + epsilon()){
//            if (lower_bound > upper_bound) {
//                break;
//            }
////            std::cerr << "Result from lb ";
//            return n.g.alpha;
//        }
//
//    }
////    std::cerr << "Result from ub ";
//    return upper_bound;
//}

double update_reference_time(const EdgeATF& path, rePEAT::Open& open_list){
    double upper_bound = std::max(path.alpha, path.beta);
    double lower_bound = path.alpha;
    std::cerr << "Starting update tref with alpha " << lower_bound << " beta " << upper_bound << " delta " << path.delta << std::endl;
    while(lower_bound < upper_bound){
        if(open_list.empty()){
            return std::numeric_limits<double>::infinity();
        }
        auto n = open_list.top();
        open_list.pop();
        std::cerr << "popped " << n.g;
        lower_bound = n.f - path.delta;
        std::cerr << ", new lb " << lower_bound << std::endl;
        if (n.g.alpha > (lower_bound + epsilon())){
            std::cerr << "Result from lb ";
            return std::max(path.alpha, lower_bound) + epsilon();
        }
    }
    std::cerr << "Result from ub ";
    return upper_bound + epsilon();
}

CompoundATF<std::vector<GraphNode *>> rePEAT::search(GraphNode * source, const Location& dest, MetaData & m,
                                                     double start_time, gamma_t gamma){
    double t_ref = start_time;
    std::vector<GraphNode *> path;
    CompoundATF solutions(path);
    m.init();
    while(t_ref < end(source->state.interval)){
        std::cerr << "tref: " << t_ref << "\n";
        Open open_list;
        open_list.emplace(EdgeATF(-std::numeric_limits<double>::infinity(), t_ref, std::numeric_limits<double>::infinity(), 0.0, gamma), 0, source, nullptr);
        auto res = asipp::search_core(open_list, dest, m);
        if(res.first.size() == 0){
            break;
        }
        solutions.add(res.second, res.first);
        t_ref = update_reference_time(res.second, open_list);
    }
    std::cerr << "At end of safe interval at start node at " << t_ref << "source int " << std::get<4>(source->state.interval) << std::endl;
    return solutions;
}