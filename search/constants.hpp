#pragma once
#include <cstdint>
#include <boost/math/constants/constants.hpp>

// BOOST_ENABLE_ASSERT_DEBUG_HANDLER is defined for the whole project

using gIndex_t = uint16_t;
using intervalTime_t = double;

// Gamma is stored as <min_gamma, max_gamma>
//using gam_item_t = std::pair<intervalTime_t, intervalTime_t>;

struct gam_item_t;

struct gam_item_t {
    intervalTime_t first;
    intervalTime_t second;
    intervalTime_t last_recovery;

    gam_item_t() = default;
    gam_item_t(intervalTime_t min_gamma, intervalTime_t max_gamma, intervalTime_t _last_recovery): first(min_gamma), second(max_gamma), last_recovery(_last_recovery) {}

    inline friend bool operator==(const gam_item_t &gam, const gam_item_t &other) {
        return gam.first == other.first && gam.second == other.second;
    }

    inline friend std::ostream& operator<< (std::ostream& stream, const gam_item_t& n){
        stream << "<" << n.first << ": " << n.second << ": " << n.last_recovery << ">";
        return stream;
    }

    inline friend gam_item_t reduce(const gam_item_t &gam, intervalTime_t reduction) {
        intervalTime_t min_gamma = std::max(gam.first - reduction, 0.0);
        intervalTime_t max_gamma = std::max(gam.second - reduction, 0.0);

        return gam_item_t(min_gamma, max_gamma, gam.last_recovery);
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

constexpr double epsilon(){
    return 0.0001;
}

constexpr double sqrt2(){
    return boost::math::double_constants::root_two;
}