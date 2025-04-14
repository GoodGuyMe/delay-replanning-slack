#pragma once
#include <functional>
#include <unordered_map>
#include <utility>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"

namespace asipp{

    template <typename Node_t>
    bool isGoal(const Node_t& n, const Location& goal_loc){
        return n.node->state.loc == goal_loc;
    }

    template <typename Node_t, typename Open_t>
    std::vector<GraphNode *> backup(const Node_t& n, Open_t& open_list){
        std::vector<GraphNode *> res;
        GraphNode* cur = n.node;
        while(cur != nullptr){
            res.push_back(cur);
            cur = open_list.parent[cur];
        }
        std::reverse(res.begin(), res.end());
        std::cout << "Arrival time: " << n.f << "\n";
        return res;
    }

    template <typename Node_t, typename Open_t>
    inline void extendOpen(const Node_t& cur, Open_t& open_list, MetaData & m, GraphEdge * successor, gamma_t gamma, long prev_id, const Node_t* previous_catf) {
        intervalTime_t gamma_after = gamma[successor->edge.agent_after.id];
        intervalTime_t gamma_before = gamma[successor->edge.agent_before.id];
        double zeta = cur.g.zeta;
        double alpha = std::max(cur.g.alpha, successor->edge.alpha - cur.g.delta + gamma_before);
        double beta = std::min(cur.g.beta, successor->edge.beta - cur.g.delta + gamma_after);
        double delta = successor->edge.delta + cur.g.delta;
        EdgeATF arrival_time_function(zeta, alpha, beta, delta, gamma);
        if (open_list.handles.contains(successor->destination)){
            auto handle = open_list.handles[successor->destination];
            if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                m.decreased++;
                double h = 0;
                open_list.decrease_key(handle ,arrival_time_function, h, successor->destination, successor->source, prev_id, previous_catf);
            }
        }
        else{
            m.generated++;
            double h = 0;
            open_list.emplace(arrival_time_function, h, successor->destination, successor->source, prev_id, previous_catf);
        }
    }

    template <typename Node_t, typename Open_t>
    inline void expand(const Node_t& cur, Open_t& open_list, const Location& goal_loc, MetaData & m){
        (void)goal_loc;
        m.expanded++;
        for(GraphEdge * successor: cur.node->successors){
            if(open_list.expanded.contains(successor->destination)){
                continue; // Already visited location and added all outgoing edges to the queue, thus the new found path to that node is worse
            }

            const Node_t *prev_catf = cur.previous_agent;
            long prev_id = cur.previous_id;
            if (prev_id != successor->edge.agent_before.id) {
//                New agent in front, store a new CATF
                Node_t copy_catf;
                copy_catf = cur;
                prev_catf = &copy_catf;
                prev_id = successor->edge.agent_before.id;
            }

            intervalTime_t gamma_after = cur.g.gamma[successor->edge.agent_after.id];
            intervalTime_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];
// || cur.g.supremum_arrival_time() <= successor->edge.zeta

//              Scenario 1 & 3
            if(cur.g.earliest_arrival_time() >= (successor->edge.beta + gamma_after)) {
                intervalTime_t buffer_needed = cur.g.earliest_arrival_time() - successor->edge.beta;
                if (buffer_needed < successor->edge.agent_after.max_buffer_time) {
                    std::cout << "----------Scenario 1-----------\n";
                    std::cout << "from " << successor->source->state << " to " << successor->destination->state << "\n";
                    std::cout << "Using " << buffer_needed << " buffer time from " << successor->edge.agent_after << "\n";
                    gamma_t new_gamma = gamma_t(cur.g.gamma);
//                    OR maybe max buffer and then later reduce buffer size
                    new_gamma[successor->edge.agent_after.id] = successor->edge.agent_after.max_buffer_time;
//                    new_gamma[successor->edge.agent_after.id] = std::min(successor->edge.agent_after.max_buffer_time, buffer_needed + 1);
                    extendOpen(cur, open_list, m, successor, new_gamma, prev_id, prev_catf);
                    for (intervalTime_t gamma : new_gamma) {
                        std::cout << gamma << ' ';
                    }
                    std::cout << std::endl;
                }
                continue;
            }
//            Scenario 2
            if((cur.g.earliest_arrival_time() < successor->edge.alpha + gamma_before) && (cur.previous_agent != nullptr)) {
                intervalTime_t buffer_needed = cur.g.earliest_arrival_time() - successor->edge.alpha;

                if (buffer_needed < successor->edge.agent_before.max_buffer_time && buffer_needed > 0) {
                    std::cout << "----------Scenario 2-----------\n";
                    std::cout << "from " << successor->source->state << " to " << successor->destination->state << "\n";
                    std::cout << "Using " << buffer_needed << " buffer time from " << successor->edge.agent_after << "\n";

                    const Node_t catf = *cur.previous_agent;
                    gamma_t new_gamma = catf.g.gamma;
                    //                new_gamma[successor->edge.agent_before.id] = cur.g.earliest_arrival_time() - successor->edge.alpha;
                    new_gamma[successor->edge.agent_before.id] = successor->edge.agent_before.max_buffer_time;
                    extendOpen(catf, open_list, m, successor, new_gamma, prev_id, catf.previous_agent);
                    for (intervalTime_t gamma: new_gamma) {
                        std::cout << gamma << ' ';
                    }
                    std::cout << std::endl;
                }
            }

            extendOpen(cur, open_list, m, successor, cur.g.gamma, prev_id, prev_catf);
        }
    }

    template<typename Open_t>
    inline void dump_open(const Open_t& open_list){
        auto cur = open_list.queue.ordered_begin();
        auto end = open_list.queue.ordered_end();
        std::cerr << "Open:";
        while(cur != end){
            std::cerr << "\t" << *cur << "\n";
            cur = std::next(cur);
        }
    }

    template<typename Open_t>
    inline std::pair<std::vector<GraphNode *>, EdgeATF> search_core(Open_t& open_list, const Location& dest, MetaData & m){
        while(!open_list.empty()){
            auto cur = open_list.top();
            if(isGoal(cur, dest)){
                auto res = std::make_pair(backup(cur, open_list), cur.g);
                return res;             
            }
            open_list.pop();
            expand(cur, open_list, dest, m);
        }
        std::cerr << "No path found " << "\n";
        return std::make_pair(std::vector<GraphNode *>(), EdgeATF());
    }

   std::pair<std::vector<GraphNode *>, EdgeATF> search(GraphNode * source, const Location& dest, MetaData & m, double start_time);
}