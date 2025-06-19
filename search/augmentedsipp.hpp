#pragma once
#include <functional>
#include <unordered_map>
#include <utility>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"
#include "repeat.hpp"

namespace asipp{

    inline gam_item_t get_reduced_gamma(const gam_item_t& gamma, NeightbouringAgent agent) {
        intervalTime_t gamma_reduction = std::max(gamma.last_recovery - agent.compound_recovery_time, 0.0);

        gam_item_t reduced = reduce(gamma, gamma_reduction);
        reduced.last_recovery = agent.compound_recovery_time;
        return reduced;
    }

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
    inline void extendOpen(const Node_t& cur, Open_t& open_list, MetaData & m, GraphNode * source, GraphNode * destination, EdgeATF edge, gamma_t gamma) {
        intervalTime_t zeta  = cur.g.zeta;
        intervalTime_t alpha = std::max(cur.g.alpha, edge.alpha - cur.g.delta);
        intervalTime_t beta  = std::min(cur.g.beta,  edge.beta  - cur.g.delta);
        intervalTime_t delta = cur.g.delta + edge.delta;

        gam_item_t gam_after = gamma[edge.agent_after.id];

        gam_after = get_reduced_gamma(gam_after, edge.agent_after);

        intervalTime_t min_gamma = std::max(gam_after.first, alpha - (edge.beta - cur.g.delta - gam_after.second));

//        intervalTime_t duration_available = beta-(edge.alpha - delta);
        intervalTime_t duration_available = std::max(0.0, beta - alpha);
        intervalTime_t max_gamma = gam_after.second;
        if (duration_available > 0.0) {
            max_gamma = std::min(duration_available + min_gamma, gam_after.second);
        }

//        gamma[edge.agent_after.id] = get_reduced_gamma(gam_item_t(min_gamma, max_gamma, gam_after.last_recovery), edge.agent_after);
        gamma[edge.agent_after.id] = gam_item_t(min_gamma, max_gamma, gam_after.last_recovery);

        EdgeATF arrival_time_function(zeta, alpha, beta, delta, gamma);

        std::cerr << "Created catf " << arrival_time_function << std::endl;

        intervalTime_t eat = cur.g.earliest_arrival_time();
        if (eat >= edge.beta) {
            std::cerr << "cur.alpha + cur.delta > edge.beta" << eat << " >= " << edge.beta << std::endl;
            return;
        }

//        if (!valid_gamma(gamma[edge.agent_after.id])) {
//            std::cerr << "Gamma not valid " << gamma[edge.agent_after.id] << std::endl;
//            return;
//        }

        if (open_list.handles.contains(MapNode(destination))){
            auto handle = open_list.handles[MapNode(destination)];
            if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                m.decreased++;
//                double h = arrival_time_function.sum_of_delays();
                double h = edge.heuristic;
                Node_t new_node = open_list.decrease_key(handle, arrival_time_function, h, destination, source);
                std::cerr << "Decreased: " << new_node << std::endl;
            } else if(arrival_time_function.beta > (*handle).g.beta) {
                std::cerr << "This line fucked with it" << std::endl;
                m.decreased++;
//                double h = arrival_time_function.sum_of_delays();
                double h = edge.heuristic;
                Node_t new_node = open_list.decrease_key(handle, arrival_time_function, h, destination, source);
                std::cerr << "Decreased: " << new_node << std::endl;
            } else {
                std::cerr << "This line still fucked with it" << std::endl << "  New:      " << arrival_time_function << std::endl << "  Existing: " << (*handle).g << std::endl;
            }
        }
        else{
            m.generated++;
//            double h = arrival_time_function.sum_of_delays();
            double h = edge.heuristic;
            Node_t new_node = open_list.emplace(arrival_time_function, h, destination, source);
            std::cerr << "Added: " << new_node << std::endl;
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
            if(open_list.expanded.contains(MapNode(successor->destination))){
                std::cerr << "Already visited " << *successor << " at an earlier time " << std::endl;
                continue; // Already visited location and added all outgoing edges to the queue, thus the new found path to that node is worse
            }
//            gam_item_t gamma_before = get_reduced_gamma(cur, successor->edge.agent_before);
//            gam_item_t gamma_after  = get_reduced_gamma(cur, successor->edge.agent_after);

            gam_item_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];
            gam_item_t gamma_after  = cur.g.gamma[successor->edge.agent_after.id];

            EdgeATF edge(successor->edge);
            edge.zeta = successor->edge.zeta + gamma_before.first;
            edge.alpha = successor->edge.alpha + gamma_before.first;
            edge.beta = successor->edge.beta + gamma_after.second;

            std::cerr << "Outgoing edge " << edge << ", b: " << gamma_before << ", a: " << gamma_after << std::endl;

//            If there is more buffer time available than is currently being used, use it.
            intervalTime_t available_buffer_time = edge.agent_after.max_buffer_time - gamma_after.second;
            if (available_buffer_time > epsilon()) {
                std::cerr << "Addition using " << available_buffer_time << " more buffer time" << std::endl;
//                For this extra atf, alpha is the beta of the old edge
//                  Beta is alpha + extra aviailable buffer time
//                  Gamma for the agent after is atleast how much was used before, and max the new max buffer time.

                EdgeATF extra_edge(edge);
                extra_edge.alpha = edge.beta;
                extra_edge.beta = extra_edge.alpha + available_buffer_time;

                gamma_t new_gamma = gamma_t(cur.g.gamma);
                new_gamma[successor->edge.agent_after.id] = gam_item_t(gamma_after.second, successor->edge.agent_after.max_buffer_time, gamma_after.last_recovery);

                std::cerr << "Additional edge " << extra_edge << ", " << new_gamma[successor->edge.agent_after.id] << std::endl;
                extendOpen(cur, open_list, m, successor->source, successor->destination, extra_edge, new_gamma);
            }

            gamma_t old_gamma = gamma_t(cur.g.gamma);
            old_gamma[successor->edge.agent_after.id] = gam_item_t(gamma_after.first, gamma_after.second,  gamma_after.last_recovery);
            extendOpen(cur, open_list, m, successor->source, successor->destination, edge, old_gamma);

//            gam_item_t gamma_after  = cur.g.gamma[successor->edge.agent_after.id];
//            gam_item_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];

//            intervalTime_t alpha = successor->edge.alpha - cur.g.delta + gamma_before.first;
//            intervalTime_t beta  = successor->edge.beta  - cur.g.delta + gamma_after.second;
//
//            intervalTime_t minimum_gamma = std::max(gamma_after.first, cur.g.earliest_arrival_time() - successor->edge.beta);
//
////            If there is available buffer time to use, create an edge that uses it.
//            if (successor->edge.agent_after.max_buffer_time - gamma_after.second > epsilon()) {
//                std::cerr << "Addition using " << successor->edge.agent_after.max_buffer_time - gamma_after.second << " more buffer time" << std::endl;
//                intervalTime_t succ_alpha = beta;
//                intervalTime_t succ_beta  = beta + successor->edge.agent_after.max_buffer_time - gamma_after.second;
//                gamma_t gamma_buffer = gamma_t(cur.g.gamma);
//                gamma_buffer[successor->edge.agent_after.id] = gam_item_t(minimum_gamma, successor->edge.agent_after.max_buffer_time, successor->edge.agent_after.compound_recovery_time);
//                extendOpen(cur, open_list, m, successor, gamma_buffer, succ_alpha, succ_beta);
//            }
////            std::cerr << "Standard addition" << std::endl;
//            intervalTime_t eat = cur.g.earliest_arrival_time();
//            if (eat >= edge.beta) {
//                std::cerr << "cur.alpha + cur.delta > edge.beta + gamma.max" << eat << " >= " << edge.beta << std::endl;
//                continue;
//            }
//            gamma_t gamma_normal = gamma_t(cur.g.gamma);
//            gamma_normal[successor->edge.agent_after.id] = gam_item_t(minimum_gamma, gamma_after.second, successor->edge.agent_after.compound_recovery_time);
//            extendOpen(cur, open_list, m, successor, gamma_normal, alpha, beta);
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