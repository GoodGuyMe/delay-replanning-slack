#pragma once
#include <cstdint>
#include <boost/math/constants/constants.hpp>

// BOOST_ENABLE_ASSERT_DEBUG_HANDLER is defined for the whole project


constexpr double epsilon(){
    return 0.0001;
}

constexpr double sqrt2(){
    return boost::math::double_constants::root_two;
}

using gIndex_t = uint16_t;
using intervalTime_t = double;

// Gamma is stored as <min_gamma, max_gamma>
//using gam_item_t = std::pair<intervalTime_t, intervalTime_t>;

struct gam_item_t;

struct gam_item_t {
    intervalTime_t first;
    intervalTime_t second;
    intervalTime_t last_recovery;
    std::string location;
    intervalTime_t initial_delay;

    gam_item_t() = default;
    gam_item_t(intervalTime_t min_gamma, intervalTime_t max_gamma, intervalTime_t _last_recovery,
               std::string delay_location, intervalTime_t _initial_delay): first(min_gamma), second(max_gamma), last_recovery(_last_recovery), location(delay_location), initial_delay(_initial_delay) {}

    inline friend bool operator==(const gam_item_t &gam, const gam_item_t &other) {
        return gam.first == other.first && gam.second == other.second;
    }

    inline friend std::ostream& operator<< (std::ostream& stream, const gam_item_t& n){
        stream << "<" << n.first << ": " << n.second << ": " << n.last_recovery << ": " << n.location << ": " << n.initial_delay << ">";
        return stream;
    }

    inline friend gam_item_t reduce(const gam_item_t &gam, intervalTime_t reduction) {
        intervalTime_t min_gamma = std::max(gam.first - reduction, 0.0);
        intervalTime_t max_gamma = std::max(gam.second - reduction, 0.0);
        intervalTime_t new_recovery = std::max(gam.last_recovery - reduction, 0.0);

        return gam_item_t(min_gamma, max_gamma, new_recovery, gam.location, gam.initial_delay);
    }

    inline friend bool valid_gamma(const gam_item_t &gam) {
        if(abs(gam.second) < epsilon()) {
            std::cerr << "Still zero" << std::endl;
            return true;
        }
        intervalTime_t diff = abs(gam.second - gam.first);
        std::cerr << "Difference " << diff << " of " << gam << std::endl;
        return diff > epsilon();
    }
};

using gamma_t = std::vector<gam_item_t>;

namespace std {
    template<>
    struct hash<gamma_t> {
        std::size_t operator()(gamma_t const &vec) const {
            std::size_t seed = vec.size();
            for (gam_item_t x: vec) {
//                seed ^= std::hash<intervalTime_t>()(x.first);
                seed ^= std::hash<intervalTime_t>()(x.second);
            }
            return seed;
        }
    };
}