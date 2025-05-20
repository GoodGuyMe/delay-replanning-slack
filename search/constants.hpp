#pragma once
#include <cstdint>
#include <boost/math/constants/constants.hpp>

// BOOST_ENABLE_ASSERT_DEBUG_HANDLER is defined for the whole project

using gIndex_t = uint16_t;
using intervalTime_t = double;

// Gamma is stored as <min_gamma, max_gamma>
using gam_item_t = std::pair<intervalTime_t, intervalTime_t>;
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