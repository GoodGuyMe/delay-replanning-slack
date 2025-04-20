#pragma once

#include <unordered_set>
#include <vector>
#include <set>
#include <limits>
#include <chrono>
#include <boost/container/flat_set.hpp>
#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_int_distribution.hpp>
#include <iostream>
#include <numeric>
#include "constants.hpp"
#include "segment.hpp"

//using NeightbouringAgent = std::tuple<int, intervalTime_t>;

struct NeightbouringAgent{
    long id;
    intervalTime_t max_buffer_time;
    intervalTime_t length_unsafe;
    NeightbouringAgent() = default;
    NeightbouringAgent(long _id, intervalTime_t _max_buffer_time, intervalTime_t _length_unsafe): id(_id), max_buffer_time(_max_buffer_time), length_unsafe(_length_unsafe){}

    inline friend std::ostream& operator<< (std::ostream& stream, const NeightbouringAgent& train){
        stream << train.id << " max: " << train.max_buffer_time << " unsafe_time: " << train.length_unsafe;
        return stream;
    }
};

struct EdgeATF;

struct EdgeATF{
    intervalTime_t zeta;
    intervalTime_t alpha;
    intervalTime_t beta;
    intervalTime_t delta;
    std::vector<EdgeATF*> successors;
    NeightbouringAgent agent_before;
    NeightbouringAgent agent_after;
    gamma_t gamma;
    EdgeATF() = default;

// Constructor for initial edge ATF
    EdgeATF(
            intervalTime_t _zeta,
            intervalTime_t _alpha,
            intervalTime_t _beta,
            intervalTime_t _delta,
            int id_b,
            intervalTime_t max_buf_b,
            intervalTime_t len_uns_b,
            int id_a,
            intervalTime_t max_buf_a,
            intervalTime_t len_uns_a)
        :
            zeta(_zeta),
            alpha(_alpha),
            beta(_beta),
            delta(_delta),
            agent_before(NeightbouringAgent(id_b, max_buf_b, len_uns_b)),
            agent_after(NeightbouringAgent(id_a, max_buf_a, len_uns_a)),
            gamma(0, 0.0)
        {};

// Constructor for CATF
    EdgeATF(
            intervalTime_t _zeta,
            intervalTime_t _alpha,
            intervalTime_t _beta,
            intervalTime_t _delta,
            gamma_t _gamma)
        :
            zeta(_zeta),
            alpha(_alpha),
            beta(_beta),
            delta(_delta),
            gamma(_gamma)
    {
        gamma = gamma_t(_gamma);
    }

    inline intervalTime_t earliest_arrival_time() const{
        return alpha + delta;
    }

    inline intervalTime_t arrival_time(intervalTime_t t) const{
        if(t < zeta || beta <= t){
            return std::numeric_limits<intervalTime_t>::infinity();
        }
        if(t < std::min(alpha, beta)){
            return earliest_arrival_time();
        }
        return t + delta;
    }

    inline intervalTime_t inclusive_arrival_time(intervalTime_t t) const{
        if(t < zeta || beta < t){
            return std::numeric_limits<intervalTime_t>::infinity();
        }
        if(t < std::min(alpha, beta)){
            return earliest_arrival_time();
        }
        return t + delta;
    }

    inline intervalTime_t supremum_arrival_time() const{
        return std::numeric_limits<double>::infinity();
    }

    inline intervalTime_t sum_of_delays() const{
        return std::reduce(gamma.begin(), gamma.end());
    }

    inline bool operator<(const EdgeATF& rhs) const{
        return earliest_arrival_time() < rhs.earliest_arrival_time();
    }
    
    inline friend std::ostream& operator<< (std::ostream& stream, const EdgeATF& eatf){
        stream << "<" << eatf.zeta << "," << eatf.alpha << "," << eatf.beta << "," << eatf.delta << ",[";
        for (intervalTime_t gam: eatf.gamma) {
            stream << gam << ";";
        }
        stream <<  "]>";
        return stream;
    }

    inline segments_small_container segments() const{
        segments_small_container res;
        double periapsis = arrival_time(alpha);
        double apoapsis = inclusive_arrival_time(beta);
        if(alpha > zeta){
            res.emplace_back(zeta, alpha, periapsis, periapsis, -1);
        }
        if(beta > alpha){
            res.emplace_back(alpha, beta, periapsis, apoapsis, -1);
        }
        return res;
    }
};

using EdgeATFList = boost::container::flat_set<EdgeATF>;

template <typename T>
struct CompoundATF{
    std::vector<EdgeATF> edge_atfs;
    std::vector<T> payload;
    std::set<Segment> segments;

    CompoundATF(const T& init){
        edge_atfs.emplace_back(
            0,
            0,
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            gamma_t()
        );
        payload.emplace_back(init);
        segments.emplace(
            0.0,
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            std::numeric_limits<double>::infinity(),
            0);
    }

    inline bool monotonic_non_decreasing() const{
        if (segments.size() < 2){
            return true;
        }
        bool res = true;
        auto a = segments.begin();
        auto b = std::next(a);
        while(b != segments.end()){
            res = res && a->y1 <= b->y0; 
            a = b;
            b++;
        }
        return res;
    } 

    inline bool bumper_to_bumper() const{
        if (segments.size() < 2){
            return true;
        }
        bool res = true;
        auto a = segments.begin();
        auto b = std::next(a);
        while(b != segments.end()){
            res = res && a->x1 == b->x0; 
            a = b;
            b++;
        }
        return res;
    }    

    inline void add_segment(const Segment& segment){
        Segment seg = segment;
        auto it = segments.lower_bound(segment);
        while(true){
            if(!overlap(seg, *it)){
                segments.emplace_hint(it, seg);
                break;
            }
            auto hull = lowerHull(*it, seg);
            seg = hull[0];
            it = segments.erase(it);
            for(int i = hull.size()-1; i > 0; i--){
                it = segments.emplace_hint(it, hull[i]);
            }
            if (it == segments.begin()) {
                segments.emplace_hint(it, seg);
                break;
            }
            it = std::prev(it);
            if(it == segments.begin()){
                segments.emplace_hint(it, seg);
                break;
            }
        }        
    }

    inline void add(const EdgeATF& e, const T& p){
        edge_atfs.emplace_back(e);
        payload.emplace_back(p);
        auto segments = e.segments();
        for(auto segment: segments){
            segment.payload = edge_atfs.size()-1;
            add_segment(segment);
        }
        assert(bumper_to_bumper());
        assert(monotonic_non_decreasing());
    }

    inline EdgeATF lookup(double t) const{
        Segment ti(t-1.0,t,0,0,0); 
        auto it = segments.lower_bound(ti);
        return edge_atfs[it->payload];
    }

    inline std::vector<double> time_lookup(std::size_t n) const{
        std::vector<double> nums;
        std::vector<Segment> seg_vec(segments.begin(), segments.end());
        nums.reserve(n);
        boost::random::mt19937 gen;
        boost::random::uniform_int_distribution<> dist(0, seg_vec.size()-1);
        for(std::size_t i = 0; i < n; i++){
            auto j = dist(gen);
            while(!std::isfinite(seg_vec[j].x1 - seg_vec[j].x0)){
                j = dist(gen);
            }
            nums.emplace_back(0.5*(seg_vec[j].x1 - seg_vec[j].x0));
        }
        auto lookup_start_time = std::chrono::high_resolution_clock::now();
        for(std::size_t i = 0; i < nums.size(); i++){
            auto res = lookup(nums[i]);
            nums[i] = res.earliest_arrival_time();
        }
        auto lookup_end_time = std::chrono::high_resolution_clock::now();
        auto lookup_duration = std::chrono::duration_cast<std::chrono::nanoseconds>(lookup_end_time - lookup_start_time);
        std::cout << "Total (n=" << n << ") Lookup time: " << lookup_duration.count() << " nanoseconds\n";
        return nums;
    }

    inline friend std::ostream& operator<< (std::ostream& stream, const CompoundATF& catf){
        std::unordered_set<long> indexes;
    
        for(const auto& segment : catf.segments){
            stream << segment << ", ";
        }
        stream << "\n";
        for(const auto& segment : catf.segments){
            for (auto j : catf.payload[segment.payload]){
                stream << *j << "\n";
            }
            stream << catf.edge_atfs[segment.payload] << "\n";
        }
        return stream;
    }
};
