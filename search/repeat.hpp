#pragma once

#include <unordered_map>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"

namespace rePEAT{
    struct Node;

    struct Node{
        EdgeATF g;
        double f;
        GraphNode * node;
        long previous_id;
        const Node *previous_agent;
        Node() = default;
        Node(EdgeATF e, double _h, GraphNode * _node, long prev_id, const Node *prev_a):g(e),f(e.earliest_arrival_time() + _h),node(_node),previous_id(prev_id), previous_agent(prev_a){}

        inline friend bool operator>(const Node& a, const Node& b){
            if(a.f == b.f){
                if(a.g.alpha == b.g.alpha){
                    return a.g.beta < b.g.beta;
                }
                return a.g.alpha < b.g.alpha;
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

        inline void emplace(EdgeATF e, double h, GraphNode * n, GraphNode * p, long prev_id, const Node *prev_a){
            parent[n] = p;
            handles[n] = queue.push(Node(e, h, n, prev_id, prev_a));
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

        inline void decrease_key(handle_t handle , EdgeATF e, double h, GraphNode * n, GraphNode * p, long prev_id, const Node *prev_a){
            parent[n] = p;
            queue.increase(handle, Node(e, h, n, prev_id, prev_a));
        }
    };

    CompoundATF<std::vector<GraphNode *>> search(GraphNode * source, const Location& dest, MetaData & m, double start_time, gamma_t gamma);
}

