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
        std::cerr << "Arrival time: " << n.f << "\n";
        return res;
    }

    template <typename Node_t, typename Open_t>
    inline void extendOpen(const Node_t& cur, Open_t& open_list, MetaData & m, GraphEdge * successor, gamma_t gamma) {
        intervalTime_t gamma_after = gamma[successor->edge.agent_after.id];
        intervalTime_t gamma_before = gamma[successor->edge.agent_before.id];
        double zeta = cur.g.zeta;
        double alpha = std::max(cur.g.alpha, successor->edge.alpha - cur.g.delta + gamma_before);
        double beta = std::min(cur.g.beta, successor->edge.beta - cur.g.delta + gamma_after);
        double delta = successor->edge.delta + cur.g.delta;
        EdgeATF arrival_time_function(zeta, alpha, beta, delta, gamma);

        if (beta <= alpha) {
            std::cerr << "Beta smaller than Alpha! " << alpha << ", " << beta << std::endl;
//            std::cerr << "Alpha cur: " << cur.g.alpha << ", edge: " << successor->edge.alpha - cur.g.delta + gamma_before << std::endl;
//            std::cerr << "Beta cur: " << cur.g.beta << ", beta: " << successor->edge.beta - cur.g.delta + gamma_after << std::endl;
//            std::cerr << "Agent before: " << successor->edge.agent_before.id << ", after: " << successor->edge.agent_before.id << std::endl;
//            std::cerr << "Gamma before: " << gamma_before << ", after: " << gamma_after << std::endl;
//            std::cerr << "Gamma: [";
//            for (intervalTime_t gam: gamma) {
//                std::cerr << gam << ", ";
//            }
//            std::cerr << "]" << std::endl;
            return;
        }

        Node_t new_node;

        if (open_list.handles.contains(successor->destination)){
            auto handle = open_list.handles[successor->destination];
            if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                m.decreased++;
                double h = 0;
                new_node = open_list.decrease_key(handle, arrival_time_function, h, successor->destination, successor->source);
            }
        }
        else{
            m.generated++;
            double h = 0;
            new_node = open_list.emplace(arrival_time_function, h, successor->destination, successor->source);
        }
        std::cerr << "New node: " << new_node << std::endl;
    }

    template <typename Node_t, typename Open_t>
    inline void expand(const Node_t& cur, Open_t& open_list, const Location& goal_loc, MetaData & m){
        (void)goal_loc;
        m.expanded++;
        std::cerr << "---------------- new node ----------------"<< std::endl;
        std::cerr << "Currently at node " << *cur.node << " at time " << cur.g.earliest_arrival_time() << " with outgoing edges destination: [";
        for(GraphEdge * successor: cur.node->successors){
            std::cerr << *successor->destination << ", ";
        }
        std::cerr << "], gamma: [";

        for (intervalTime_t gamma : cur.g.gamma) {
            std::cerr << gamma << ", ";
        }
        std::cerr << "]" << std::endl;

        for(GraphEdge * successor: cur.node->successors){
            if(open_list.expanded.contains(successor->destination)){
                continue; // Already visited location and added all outgoing edges to the queue, thus the new found path to that node is worse
            }
            std::cerr << "+++++++++++++ new successor +++++++++++++"<< std::endl;
            intervalTime_t gamma_after  = cur.g.gamma[successor->edge.agent_after.id];
            intervalTime_t gamma_before = cur.g.gamma[successor->edge.agent_before.id];
// || cur.g.supremum_arrival_time() <= successor->edge.zeta

//              Scenario 1 & 3
//            if(cur.g.earliest_arrival_time() >= (successor->edge.beta + gamma_after)) {
//                Limit usage of buffer time by how long the unsafe interval is that follows the safe interval
//            intervalTime_t buffer_needed = cur.g.earliest_arrival_time() - successor->edge.beta;

            intervalTime_t length_unsafe_after = successor->edge.agent_after.length_unsafe;
            std::cerr << "----------Scenario 1-----------\n";
            std::cerr << "from " << successor->source->state << " to " << successor->destination->state << "\n";
//            std::cerr << "Using " << buffer_needed << " buffer time from " << successor->edge.agent_after << "\n";
            std::cerr << "Length unsafe after: " << length_unsafe_after << "\n";

//            buffer_needed = std::min(buffer_needed, length_unsafe_after);

//            if (buffer_needed < successor->edge.agent_after.max_buffer_time) {
            if (length_unsafe_after < successor->edge.agent_after.max_buffer_time) {
                gamma_t gamma_1 = gamma_t(cur.g.gamma);
                gamma_1[successor->edge.agent_after.id] = length_unsafe_after;
                std::cerr << "Addition scenario 1" << std::endl;
                extendOpen(cur, open_list, m, successor, gamma_1);
            }
            gamma_t gamma_2 = gamma_t(cur.g.gamma);
            gamma_2[successor->edge.agent_after.id] = successor->edge.agent_after.max_buffer_time;
            extendOpen(cur, open_list, m, successor, gamma_2);
//            }
            std::cerr << "Standard addition" << std::endl;
            extendOpen(cur, open_list, m, successor, cur.g.gamma);
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