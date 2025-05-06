#pragma once

#include <unordered_map>
#include <boost/heap/d_ary_heap.hpp>
#include "graph.hpp"


struct MapNode;

struct MapNode {
    GraphNode *graphNode;
    gamma_t gamma;

    MapNode() = default;
    MapNode(GraphNode *_graphNode, gamma_t _gamma): graphNode(_graphNode), gamma(_gamma) {}

    bool operator==(const MapNode &rhs) const {
        return (graphNode == rhs.graphNode && gamma == rhs.gamma);
    }
};

namespace std {
    template<>
    struct hash<MapNode> {
        inline size_t operator()(const MapNode& mn) const {
            return ((hash<GraphNode *>()(mn.graphNode) ^ (hash<gamma_t >()(mn.gamma) << 1)) >> 1);
        }
    };
}


namespace rePEAT{
    struct Node;

    struct Node{
        EdgeATF g;
        double f;
        GraphNode * node;
        Node() = default;
        Node(EdgeATF e, double _h, GraphNode * _node):g(e),f(e.alpha + _h),node(_node){}

        inline friend bool operator>(const Node& a, const Node& b){
            if(a.f == b.f){
                if (a.g.sum_of_delays() == b.g.sum_of_delays()) {
                    if (a.g.alpha == b.g.alpha) {
                        return a.g.beta < b.g.beta;
                    }
                    return a.g.alpha < b.g.alpha;
                }
                return a.g.sum_of_delays() > b.g.sum_of_delays();
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
        std::unordered_map<MapNode, handle_t> handles;
        std::unordered_map<MapNode, double> expanded;

        inline Node emplace(EdgeATF e, double h, GraphNode * n, GraphNode * p){
            parent[n] = p;
            Node new_node = Node(e, h, n);
            handles[MapNode(n, e.gamma)] = queue.push(new_node);
            return new_node;
        }

        inline bool empty() const{
            return queue.empty();
        }

        inline Node top() const{
            return queue.top();
        }

        inline void pop(){
            Node n = top();
            expanded[MapNode(n.node, n.g.gamma)] = n.g.earliest_arrival_time();
            queue.pop();
        }

        inline Node decrease_key(handle_t handle , EdgeATF e, double h, GraphNode * n, GraphNode * p){
            parent[n] = p;
            Node new_node = Node(e, h, n);
            queue.increase(handle, new_node);
            return new_node;
        }

        inline size_t size() {
            return queue.size();
        }
    };

    CompoundATF<std::vector<GraphNode *>> search(GraphNode * source, const Location& dest, MetaData & m, double start_time, gamma_t gamma);
}

