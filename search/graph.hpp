#pragma once

#include <boost/container/flat_set.hpp>
#include <boost/unordered/unordered_flat_map.hpp>
#include "structs.hpp"
#include "atf.hpp"

struct GraphEdge;
struct GraphNode;

struct GraphNode{
    State state;
    boost::container::flat_set<GraphEdge *> successors;
    GraphNode() = default;
    GraphNode(const State& s):state(s){}
    inline friend std::ostream& operator<<(std::ostream& stream, const GraphNode& gn){
        stream << gn.state << " ns:" << gn.successors.size();
        return stream;
    }

    bool operator==(const GraphNode &rhs) const {
        return state == rhs.state;
    }

    bool operator!=(const GraphNode &rhs) const {
        return !(rhs == *this);
    }
};

struct GraphEdge{
    EdgeATF edge;
    GraphNode * source;
    GraphNode * destination;
    GraphEdge(const EdgeATF& e):edge(e){
        source = nullptr;
        destination = nullptr;
    }
    inline friend std::ostream& operator<< (std::ostream& stream, const GraphEdge& ge){
        stream << ge.edge << " " << *ge.source << "->" << *ge.destination;
        return stream;
    }

    inline friend bool operator<(const GraphEdge& lhs, double rhs){
        return lhs.edge.earliest_arrival_time() < rhs;
    }

    inline friend bool operator<(const GraphEdge& lhs, const GraphEdge& rhs){
        return lhs < rhs.edge.earliest_arrival_time();
    }
};

struct Graph{
    std::vector<GraphEdge> edges;
    std::vector<GraphNode> node_array;
    long n_agents;
    boost::unordered::unordered_flat_map<State, GraphNode *, std::hash<State>> nodes;
    Graph() = default;
    inline void dump() const{
        for (const auto & n: nodes){
            std::cout << *n.second;
            std::cout << " succ:\n";
            for (const auto& s: n.second->successors){
                std::cout << "\t" << *s  << "\n";
            }
            std::cout << "\n";
        }
        for (const auto& e: edges){
            std::cout << e << "\n";
        }
    }
    inline friend std::ostream& operator<< (std::ostream& stream, const Graph& g){
        stream << g.edges.size() << " edges, " << g.nodes.size() << " nodes";       
        return stream;
    }
};

Graph read_graph(std::string filename);
GraphNode * find_earliest(Graph& g, Location loc, double start_time);