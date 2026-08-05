#ifndef SHAPE_METRICS_HPP_
#define SHAPE_METRICS_HPP_

/**
 * A plain data struct. cppwg wraps it as a normal class (issue #116); it does
 * not need to be a class or to wrap a single enum. Its public data members are
 * exposed to Python with def_readwrite, except:
 *   - `dimension` is const, so it is bound read-only (def_readonly);
 *   - `scratch` is suppressed via the `excluded_variables` config option.
 */
struct ShapeMetrics
{
    double area;
    double perimeter;
    const unsigned dimension = 2;
    int scratch;
};

#endif // SHAPE_METRICS_HPP_
