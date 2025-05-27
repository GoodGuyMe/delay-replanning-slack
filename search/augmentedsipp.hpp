#pragma once
#include <functional>
#include <unordered_map>
#include <utility>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"
#include "repeat.hpp"

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
        return res;
    }

    template <typename Node_t, typename Open_t>
    inline void extendOpen(const Node_t& cur, Open_t& open_list, MetaData & m, GraphEdge * successor, gamma_t gamma, intervalTime_t succ_alpha, intervalTime_t succ_beta) {
        intervalTime_t zeta = cur.g.zeta;
        intervalTime_t alpha = std::max(cur.g.alpha, succ_alpha);
        intervalTime_t beta = std::min(cur.g.beta, succ_beta);
        intervalTime_t delta = successor->edge.delta + cur.g.delta;

        intervalTime_t duration_available = beta-alpha;
        gam_item_t gam_after = gamma[successor->edge.agent_after.id];
        intervalTime_t max_gamma = std::min(duration_available + gam_after.first, gam_after.second);
        gamma[successor->edge.agent_after.id].second = max_gamma;

        EdgeATF arrival_time_function(zeta, alpha, beta, delta, gamma);

        if (!valid_gamma(gamma[successor->edge.agent_after.id])) {
            std::cerr << "Gamma not valid " << gamma[successor->edge.agent_after.id] << std::endl;
            return;
        }

        if (beta <= alpha) {
//            std::cerr << "Beta smaller than Alpha! " << alpha << ", " << beta << std::endl;
            return;
        }

        if (open_list.handles.contains(MapNode(successor->destination, gamma))){
            auto handle = open_list.handles[MapNode(successor->destination, gamma)];
            if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                m.decreased++;
//                double h = arrival_time_function.sum_of_delays();
                double h = 0;
                Node_t new_node = open_list.decrease_key(handle, arrival_time_function, h, successor->destination, successor->source);
//                std::cerr << "Decreased: " << new_node << std::endl;
            } else {
//                std::cerr << "This line fucked with it" << std::endl;
            }
        }
        else{
            m.generated++;
//            double h = arrival_time_function.sum_of_delays();
            double h = 0;
            Node_t new_node = open_list.emplace(arrival_time_function, h, successor->destination, successor->source);
//            std::cerr << "Added: " << new_node << std::endl;
        }
    }

    template <typename Node_t, typename Open_t>
    inline void expand(const Node_t& cur, Open_t& open_list, const Location& goal_loc, MetaData & m){
        (void)goal_loc;
        m.expanded++;
        std::cerr << "---------------- new node ----------------"<< std::endl;
        std::cerr << "At node " << *cur.node << ", time " << cur.g.earliest_arrival_time();
        std::cerr << "\n  g: " << cur.g << std::endl;

        for(GraphEdge * successor: cur.node->successors){
            if(open_list.expanded.contains(MapNode(successor->destination, successor->edge.gamma))){
                std::cerr << "Skipped successor " << successor << std::endl;
                continue; // Already visited location and added all outgoing edges to the queue, thus the new found path to that node is worse
            }
            gam_item_t gamma_after  = get_reduced_gamma(cur, successor->edge.agent_after);
            gam_item_t gamma_before = get_reduced_gamma(cur, successor->edge.agent_before);

//            gam_item_t gamma_after  = cur.g.gamma[successor->edge.agent_after.id];
//            gam_item_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];

            intervalTime_t alpha = successor->edge.alpha - cur.g.delta + gamma_before.second;
            intervalTime_t beta  = successor->edge.beta  - cur.g.delta + gamma_after.second;

            intervalTime_t minimum_gamma = std::max(gamma_after.first, cur.g.earliest_arrival_time() - successor->edge.beta);

//            If there is available buffer time to use, create an edge that uses it.
            if (successor->edge.agent_after.max_buffer_time - gamma_after.second > 0) {
//                std::cerr << "Addition with buffer time" << std::endl;
                intervalTime_t succ_alpha = beta;
                intervalTime_t succ_beta  = beta + successor->edge.agent_after.max_buffer_time - gamma_after.second;
                gamma_t gamma_buffer = gamma_t(cur.g.gamma);
                gamma_buffer[successor->edge.agent_after.id] = gam_item_t(minimum_gamma, successor->edge.agent_after.max_buffer_time, successor->edge.agent_after.compound_recovery_time);
                extendOpen(cur, open_list, m, successor, gamma_buffer, succ_alpha, succ_beta);
            }
//            std::cerr << "Standard addition" << std::endl;
            gamma_t gamma_normal = gamma_t(cur.g.gamma);
            gamma_normal[successor->edge.agent_after.id] = gam_item_t(minimum_gamma, gamma_after.second, successor->edge.agent_after.compound_recovery_time);
            extendOpen(cur, open_list, m, successor, gamma_normal, alpha, beta);
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
//            std::cerr << "Queue has " << open_list.size() << " elements." << std::endl;
            auto cur = open_list.top();
            if(isGoal(cur, dest)){
                auto res = std::make_pair(backup(cur, open_list), cur.g);
//                open_list.pop();
                std::cerr << "found path: " << cur.g << std::endl;
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