#pragma once

#include <iostream>
#include <boost/container/flat_set.hpp>
#include <boost/unordered/unordered_flat_map.hpp>
#include <boost/functional/hash.hpp>
#include "constants.hpp"


using SafeInterval = std::pair<intervalTime_t, intervalTime_t>;

inline intervalTime_t begin(const SafeInterval& si){
    return si.second;
}

inline intervalTime_t end(const SafeInterval& si){
    return si.first;
}

inline bool contains(const SafeInterval& si, intervalTime_t t){
    return begin(si) <= t && t < end(si);
}

inline bool overlap(const SafeInterval& left, const SafeInterval& right){
    auto earliest = std::min(begin(left), begin(right));
    auto latest = std::max(end(left), end(right));
    return latest - earliest <= end(left) - begin(left) + end(right) - begin(right);
}

struct Location{
        std::string name;
        Location() = default;
        Location(std::string n):name(n){}
        constexpr bool operator ==(const Location & l) const{
            return name == l.name;
        }
        inline friend std::ostream& operator<< (std::ostream& stream, const Location& loc){
            stream << loc.name;
            return stream;
        }
};

namespace std {
    template<>
    struct hash<Location> {
        inline size_t operator()(const Location& loc) const {
            boost::hash<std::string> hasher;
            return hasher(loc.name);
        }
    };
}

struct State{
    Location loc;
    SafeInterval interval;
    State() = default;
    State(std::string n, double s, double e):loc(n),interval(e,s){}; 
    constexpr bool operator ==(const State & s) const{
        return loc == s.loc && interval == s.interval;
    }
    inline friend std::ostream& operator<< (std::ostream& stream, const State& s){
        stream << s.loc << " <" << s.interval.second << "," << s.interval.first << ">";
        return stream;
    }
};

namespace std {
    template<>
    struct hash<State> {
        inline std::size_t operator()(const State& s) const {
            std::size_t seed = 0;
            boost::hash_combine(seed, s.loc.name);
            boost::hash_combine(seed, s.interval.second);
            boost::hash_combine(seed, s.interval.second);
            return seed;
        }
    };
}

struct MetaData{
    long generated;
    long expanded;
    long decreased;

    inline void init(){
        generated = 0;
        expanded = 0;
        decreased = 0;
    }
    inline friend std::ostream& operator<< (std::ostream& stream, const MetaData& m){
        stream << "Nodes generated: " << m.generated << " Nodes decreased: " << m.decreased << " Nodes expanded: " << m.expanded; 
        return stream;
    }
};