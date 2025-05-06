#include <iostream>
#include <filesystem>
#include <ostream>
#include <chrono>
#include <boost/program_options.hpp>
#include "structs.hpp"
#include "graph.hpp"
#include "repeat.hpp"

namespace po = boost::program_options;

int main(int argc, char* argv[]) {
    try{
        po::options_description desc("Allowed options");
        desc.add_options()
        ("help,h", "produce help message")
        ("start,x", po::value<std::string>(), "starting location")
        ("goal,y", po::value<std::string>(), "goal location")
        ("edgegraph,g", po::value<std::filesystem::path>(),"gzip'd file containing the edge arrival time functions.")
        ("search,s", po::value<std::string>()->default_value("repeat"), "Search algorithm to use")
        ("startTime,t", po::value<double>()->default_value(0.0), "Start Time of search.")
        ("lookups,l", po::value<long>()->default_value(100), "Number of lookups to test repeat")
        ;
        po::variables_map vm;
        po::store(po::parse_command_line(argc, argv, desc), vm);
        po::notify(vm); 

        if (vm.count("help")){
            std::cout << desc << std::endl;
        }
        else if(vm.count("edgegraph") && std::filesystem::is_regular_file(vm["edgegraph"].as<std::filesystem::path>())){
            Location source_loc(vm["start"].as<std::string>());
            Location goal_loc(vm["goal"].as<std::string>());

            Graph g = read_graph(vm["edgegraph"].as<std::filesystem::path>().string());

            bool foundStart = false;
            bool foundGoal = false;
            for (GraphNode n: g.node_array) {
                if (n.state.loc == source_loc) foundStart = true;
                if (n.state.loc == goal_loc) foundGoal = true;
            }
            if (!foundStart){
                std::cout << "[ERROR] Start location {" << source_loc.name << "} does not exist in graph\n";
            } 
            if (!foundGoal){
                std::cout << "[ERROR] Goal location {" << goal_loc.name << "} does not exist in graph\n";
            }

            double start_time = vm["startTime"].as<double>();
            GraphNode * source = find_earliest(g, source_loc, start_time);

            MetaData m;
            gamma_t initial_gamma(g.n_agents + 1);

            auto search_start_time = std::chrono::high_resolution_clock::now();
            auto res = rePEAT::search(source, goal_loc, m, start_time, initial_gamma);
            auto search_time = std::chrono::high_resolution_clock::now();
            auto search_duration = std::chrono::duration_cast<std::chrono::nanoseconds>(search_time - search_start_time);

            std::flush(std::cerr);
            std::cout << m << "\n";
            std::cout << res;
            std::cout << "Search time: " << search_duration.count() << " nanoseconds\n";
            std::flush(std::cout);

            auto c = res.time_lookup(vm["lookups"].as<long>());
        }
        else{
            std::cout << desc << std::endl;
        }
        
    }
    catch (const po::error &ex){
        std::cerr << ex.what() << std::endl;
    }
    return 0;
}
