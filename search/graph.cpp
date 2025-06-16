#include <iostream>
#include <fstream>
#include <boost/iostreams/device/file.hpp>
#include <boost/iostreams/stream_buffer.hpp>
#include "constants.hpp"
#include "graph.hpp"

struct inATF{
    long source;
    long dest;
    EdgeATF eATF;
    inATF(long s, long d, EdgeATF e):source(s),dest(d),eATF(e){}
};

void read_ATF(std::istream& i, std::vector<inATF>& res){
    long x, y;
    std::string s;
    if(!(i >> x)){return;}
    i >> y;
    intervalTime_t zeta, alpha, beta, delta, crt_b, max_buf_a, crt_a, h;
    int id_b, id_a;
    i >> s;
    zeta = stod(s);
    i >> s;
    alpha = stod(s);
    i >> s;
    beta = stod(s);
    i >> s;
    delta = stod(s);
    i >> s;
    id_b = stoi(s);
    i >> s;
    crt_b = stod(s);
    i >> s;
    id_a = stoi(s);
    i >> s;
    max_buf_a = stod(s);
    i >> s;
    crt_a = stod(s);
    i >> s;
    h = stod(s);
    EdgeATF edge(zeta, alpha, beta, delta, id_b, crt_b, id_a, max_buf_a, crt_a, h);
    res.emplace_back(x, y, edge);
}

Graph read_graph(std::string filename){
    boost::iostreams::file_source fileSource(filename);

    if (!fileSource.is_open()) {
        std::cerr << "Failed to open file: " << filename << std::endl;
    }
    // Create a stream buffer from the file source
    boost::iostreams::stream_buffer<boost::iostreams::file_source> buf(fileSource);

    // Attach the buffer to an istream
    std::istream instream(&buf);

    std::vector<inATF> res;
    Graph g;
    long n_nodes;
    long n_edges;
    long n_agents;
    std::string s;
    std::string name;
    instream >> s >> s >> n_nodes;
    instream >> s >> s >> n_edges;
    g.nodes.reserve(n_nodes);
    g.node_array.reserve(n_nodes);
    std::cerr << "start nodes read\n";
    std::flush(std::cerr);
    for (long i = 0; i < n_nodes; i++){
        double st, en, buf_a;
        int id_b, id_a;
        instream >> name;
        instream >> s;
        st = stod(s);
        instream >> s;
        en = stod(s);
        instream >> s;
        id_b = stoi(s);
        instream >> s;
        id_a = stoi(s);
        instream >> s;
        buf_a = stod(s);
        State state(name, st, en, id_b, id_a, buf_a);
        g.node_array.emplace_back(state);
        g.nodes.emplace(state, &g.node_array.back());
        std::cerr << state << std::endl;
    }
    std::cerr << "nodes read\n";
    std::flush(std::cerr);
    for (long i = 0; i < n_edges; i++){
        read_ATF(instream, res);
    }
    instream >> s >> n_agents;
    g.n_agents = n_agents;
    g.edges.reserve(2*res.size());
    for (const auto & entry: res){
        g.edges.emplace_back(entry.eATF);
        g.edges.back().source = &g.node_array[entry.source];
        g.edges.back().destination = &g.node_array[entry.dest];
        g.node_array[entry.source].successors.emplace_hint(g.node_array[entry.source].successors.end(), &g.edges.back());
    }
    return g;
}

GraphNode *  find_earliest(Graph& g, Location loc, double start_time){
    GraphNode * cur = nullptr;
    for (auto& node: g.nodes){
        if (loc == node.first.loc && contains(node.first.interval, start_time) && (cur == nullptr || begin(cur->state.interval) > begin(node.first.interval))){
            cur = node.second;
        }
    }
    if(cur == nullptr){
        std::cerr << "Error: unable to find safe starting state: tried to find ";
        std::cerr << loc << " at time t=" << start_time << "\n";
        exit(-1);
    }
    return cur;
}
