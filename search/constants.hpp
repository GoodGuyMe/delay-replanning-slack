#pragma once
#include <cstdint>
#include <boost/math/constants/constants.hpp>

// BOOST_ENABLE_ASSERT_DEBUG_HANDLER is defined for the whole project

using gIndex_t = uint16_t;
using intervalTime_t = double;

constexpr double epsilon(){
    return 0.0001;
}

constexpr double sqrt2(){
    return boost::math::double_constants::root_two;
}