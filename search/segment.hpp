#pragma once

#include <limits>
#include <ostream>
#include <cassert>
#include <cmath>
#include <iostream>
#include <boost/container/small_vector.hpp>

struct Segment{
    double x0;
    double x1;
    double y0;
    double y1;
    long payload;
    Segment() = default;
    Segment(double b, double e, double s, double a, long p):x0(b),x1(e),y0(s),y1(a),payload(p){
        assert(x0 < x1);
        assert(y0 <= y1 || (!std::isfinite(y0)));
    }

    inline void assertfinite() const{
        assert(std::isfinite(x0));
        assert(std::isfinite(x1));
        assert(std::isfinite(y0));
        assert(std::isfinite(y1));
    }

    inline bool isFlat() const{
        return y0 == y1;
    }

    inline void assert_flat() const{
        assert(isFlat());
    }
    inline void assert_rising() const{
        assert(y0 < y1);
    }

    inline double y_inc(double x) const{
        if(x < x0 || x > x1){
            return std::numeric_limits<double>::infinity();
        }
        if(y0 == y1){
            return y0;
        }
        if(x == x0){
            return y0;
        }
        if(x == x1){
            return y1;
        }
        return y0 + (x - x0)*(y1 - y0)/(x1 - x0);
    }

    inline double y_exc(double x) const{
        if(x <= x0 || x >= x1){
            return std::numeric_limits<double>::infinity();
        }
        if(y0 == y1){
            return y0;
        }
        if(x == x0){
            return y0;
        }
        if(x == x1){
            return y1;
        }
        return y0 + (x - x0)*(y1 - y0)/(x1 - x0);
    }

    inline Segment constrain(double s, double e) const{
        double y0, y1;
        if(s == x0){
            y0 = y_inc(s);
        }
        else{
            y0 = y_exc(s);
        }
        if(e == x1){
            y1 = y_inc(e);
        }
        else{
            y1 = y_exc(e);
        }
        return Segment(s, e, y0, y1, payload);
    }


    inline bool operator<(const Segment& seg) const{
        return x1 < seg.x1;
    }

    inline bool operator==(const Segment& seg) const{
        return x0 == seg.x0 && x1 == seg.x1 && y0 == seg.y0 && y1 == seg.y1;
    }

    inline friend std::ostream& operator<< (std::ostream& stream, const Segment& seg){
        stream << "<" << seg.x0 << "," << seg.x1 << "," << seg.y0 << "," << seg.y1 << ">";
        return stream;
    }
};
using segments_small_container = boost::container::small_vector<Segment, 4>;
bool overlap(const Segment& left, const Segment& right);
segments_small_container lowerHull(const Segment& a, const Segment& b);
