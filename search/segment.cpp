#include <iostream>
#include <array>
#include <algorithm>
#include "segment.hpp"

bool overlap(const Segment& left, const Segment& right){
    auto earliest = std::min(left.x0, right.x0);
    auto latest = std::max(left.x1, right.x1);
    return latest - earliest <= left.x1 - left.x0 + right.x1 - right.x0 || left.x1 == right.x0;
}

inline void intersection(segments_small_container& res, const Segment& a, const Segment& b){
    assert(a.x0 == b.x0);
    assert(a.x1 == b.x1);
    assert(a.y0 < b.y0 && a.y1 > b.y1);
    a.assert_rising();
    b.assert_flat();
    double y_inter = b.y0;
    double x_inter = a.x0 + (y_inter - a.y0)*((a.x1 - a.x0)/(a.y1 - a.y0));
    assert(a.x0 < x_inter);
    assert(x_inter < a.x1);
    res.emplace_back(a.x0, x_inter, a.y0, y_inter, a.payload);
    res.emplace_back(x_inter, b.x1, y_inter, y_inter, b.payload);
}

inline void lowerHullHelper(segments_small_container& res, double s, double e, const Segment& a, const Segment& b){
    assert(s < e);
    Segment ac = a.constrain(s, e);
    Segment bc = b.constrain(s, e);
    if(ac.y0 > bc.y0){
        std::swap(ac, bc);
    }
    assert(ac.y0 <= bc.y0);
    if(ac.y0 < bc.y0 && bc.y1 < ac.y1){
        intersection(res, ac, bc);
        return;
    }
    if(bc.y1 < ac.y1){
        res.emplace_back(bc);
        return;
    }
    res.emplace_back(ac);
    return;
}

segments_small_container fixup(segments_small_container segs){
    segments_small_container res;
    if(segs.empty()){
        return segs;
    }
    Segment acc = segs[0];
    for(int i = 1; i < (int)segs.size(); i++){
        if(acc.payload == segs[i].payload && acc.x1 == segs[i].x0 && acc.y1 == segs[i].y0 && acc.isFlat() == segs[i].isFlat()){
            acc.x1 = segs[i].x1;
            acc.y1 = segs[i].y1;
        }
        else{
            res.push_back(acc);
            acc = segs[i];
        }
    }
    res.push_back(acc);
    return res;
}

segments_small_container lowerHull(const Segment& a, const Segment& b){
    std::cout << a << " " << b << "\n";
    assert(overlap(a, b));
    segments_small_container res;
    std::array<double, 4> breakpoints = {a.x0, a.x1, b.x0, b.x1};
    std::sort(breakpoints.begin(), breakpoints.end());
    for(int i = 0; i < 3; i++){
        double s = breakpoints[i];
        double e = breakpoints[i+1];
        if(s == e){
            continue;
        }
        lowerHullHelper(res, s, e, a, b);
    }
    assert(res.size() <= 4);
    return fixup(res);
}