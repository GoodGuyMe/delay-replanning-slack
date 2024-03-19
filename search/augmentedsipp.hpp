#pragma once
#include <functional>
#include <unordered_map>
#include <utility>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"

namespace asipp{
    struct Node;

    struct Node{
        EdgeATF g;
        double f;
        GraphNode * node;
        Node() = default;
        Node(EdgeATF e, double _h, GraphNode * _node):g(e),f(e.earliest_arrival_time() + _h),node(_node){}

        inline friend bool operator>(const Node& a, const Node& b){
            if(a.f == b.f){
                return a.g < b.g;
            }
            return a.f > b.f;
        }

        inline friend std::ostream& operator<< (std::ostream& stream, const Node& n){
            stream << *n.node << " g:" << n.g << ", f:" << n.f;
            return stream;
        }
    };

    struct NodeComp{
        bool operator()(const Node * a, const Node * b){
            return *a > *b;
        }
    };

    using Queue = boost::heap::d_ary_heap<Node, boost::heap::arity<4>, boost::heap::mutable_<true>, boost::heap::compare<std::greater<Node>>>;
    typedef typename Queue::handle_type handle_t;
    struct Open{
        Queue queue;
        std::unordered_map<GraphNode *, GraphNode *> parent;
        std::unordered_map<GraphNode *, handle_t> handles;
        std::unordered_map<GraphNode *, double> expanded;

        inline void emplace(EdgeATF e, double h, GraphNode * n, GraphNode * p){
            parent[n] = p;
            handles[n] = queue.push(Node(e, h, n));
        }

        inline bool empty() const{
            return queue.empty();
        }

        inline Node top() const{
            return queue.top();
        }

        inline void pop(){
            Node n = top();
            expanded[n.node] = n.g.earliest_arrival_time();
            queue.pop();
        }

        inline void decrease_key(handle_t handle , EdgeATF e, double h, GraphNode * n, GraphNode * p){
            parent[n] = p;
            queue.increase(handle, Node(e, h, n));
        }
    };

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
    inline void expand(const Node_t& cur, Open_t& open_list, const Location& goal_loc, MetaData & m){
        (void)goal_loc;
        m.expanded++;
        double zeta = cur.g.zeta;
        for(GraphEdge * successor: cur.node->successors){
            if(cur.g.earliest_arrival_time() >= successor->edge.beta || cur.g.supremum_arrival_time() <= successor->edge.zeta){
                continue;
            } 
            double alpha = std::max(cur.g.alpha, successor->edge.alpha - cur.g.delta);
            double beta = std::min(cur.g.beta, successor->edge.beta - cur.g.delta);
            double delta = successor->edge.delta + cur.g.delta;
            EdgeATF arrival_time_function(zeta, alpha, beta, delta);
            if(open_list.expanded.contains(successor->destination)){
                continue;
            }
            else if (open_list.handles.contains(successor->destination)){
                auto handle = open_list.handles[successor->destination];
                if(arrival_time_function.earliest_arrival_time() < (*handle).g.earliest_arrival_time()){
                    m.decreased++;
                    double h = 0;
                    open_list.decrease_key(handle ,arrival_time_function, h, successor->destination, successor->source);
                }
            }
            else{
                m.generated++;
                double h = 0;
                open_list.emplace(arrival_time_function, h, successor->destination, successor->source);
            }
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
        return std::make_pair(std::vector<GraphNode *>(), EdgeATF());
    }

   std::pair<std::vector<GraphNode *>, EdgeATF> search(GraphNode * source, const Location& dest, MetaData & m, double start_time = 0.0);
}