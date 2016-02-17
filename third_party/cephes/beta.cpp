#include "consts.hpp"
#include "gamma.hpp"

#include <math.h>
#include <boost/numeric/conversion/cast.hpp>


namespace cephes {

constexpr double MAXGAM = 171.624376956302725;

constexpr double ASYMP_FACTOR = 1e6;

double lbeta_asymp(double a, double b, int *sgn);
double lbeta_negint(int a, double b);
double beta_negint(int a, double b);

double beta(double a, double b)
{
    double y;
    int sign = 1;

    if (a <= 0.0) {
        if (a == std::floor(a)) {
            if (a == boost::numeric_cast<int>(a)) {
                return beta_negint(boost::numeric_cast<int>(a), b);
            }
            else {
                goto overflow;
            }
        }
    }

    if (b <= 0.0) {
        if (b == std::floor(b)) {
            if (b == boost::numeric_cast<int>(b)) {
                return beta_negint(boost::numeric_cast<int>(b), a);
            }
            else {
                goto overflow;
            }
        }
    }

    if (std::fabs(a) < std::fabs(b)) {
        y = a; a = b; b = y;
    }

    if (std::fabs(a) > ASYMP_FACTOR * std::fabs(b) && a > ASYMP_FACTOR) {
        /* Avoid loss of precision in lgam(a + b) - lgam(a) */
        y = lbeta_asymp(a, b, &sign);
        return sign * std::exp(y);
    }

    y = a + b;
    if (std::fabs(y) > MAXGAM || std::fabs(a) > MAXGAM || std::fabs(b) > MAXGAM) {
	int sgngam;
	y = lgam_sgn(y, &sgngam);
	sign *= sgngam;		/* keep track of the sign */
	y = lgam_sgn(b, &sgngam) - y;
	sign *= sgngam;
	y = lgam_sgn(a, &sgngam) + y;
	sign *= sgngam;
	if (y > MAXLOG) {
	    goto overflow;
	}
	return (sign * std::exp(y));
    }

    y = Gamma(y);
    a = Gamma(a);
    b = Gamma(b);
    if (y == 0.0)
        goto overflow;

    if (std::fabs(std::fabs(a) - std::fabs(y)) > std::fabs(std::fabs(b) - std::fabs(y))) {
        y = b / y;
        y *= a;
    }
    else {
        y = a / y;
        y *= b;
    }

    return (y);

overflow:
    return (sign * INFINITY);
}


/* Natural log of |beta|. */

double lbeta(double a, double b)
{
    double y;
    int sign;

    sign = 1;

    if (a <= 0.0) {
        if (a == std::floor(a)) {
            if (a == boost::numeric_cast<int>(a)) {
                return lbeta_negint(boost::numeric_cast<int>(a), b);
            }
            else {
                goto over;
            }
        }
    }

    if (b <= 0.0) {
        if (b == std::floor(b)) {
            if (b == boost::numeric_cast<int>(b)) {
                return lbeta_negint(boost::numeric_cast<int>(b), a);
            }
            else {
                goto over;
            }
        }
    }

    if (std::fabs(a) < std::fabs(b)) {
        y = a; a = b; b = y;
    }

    if (std::fabs(a) > ASYMP_FACTOR * std::fabs(b) && a > ASYMP_FACTOR) {
        /* Avoid loss of precision in lgam(a + b) - lgam(a) */
        y = lbeta_asymp(a, b, &sign);
        return y;
    }

    y = a + b;
    if (std::fabs(y) > MAXGAM || std::fabs(a) > MAXGAM || std::fabs(b) > MAXGAM) {
	int sgngam;
	y = lgam_sgn(y, &sgngam);
	sign *= sgngam;		/* keep track of the sign */
	y = lgam_sgn(b, &sgngam) - y;
	sign *= sgngam;
	y = lgam_sgn(a, &sgngam) + y;
	sign *= sgngam;
	return (y);
    }

    y = Gamma(y);
    a = Gamma(a);
    b = Gamma(b);
    if (y == 0.0) {
      over:
        return (sign * INFINITY);
    }

    if (std::fabs(std::fabs(a) - std::fabs(y)) > std::fabs(std::fabs(b) - std::fabs(y))) {
        y = b / y;
        y *= a;
    }
    else {
        y = a / y;
        y *= b;
    }

    if (y < 0) {
	y = -y;
    }

    return std::log(y);
}

/*
 * Asymptotic expansion for  ln(|B(a, b)|) for a > ASYMP_FACTOR*max(|b|, 1).
 */
double lbeta_asymp(double a, double b, int *sgn)
{
    double r = lgam_sgn(b, sgn);
    r -= b * std::log(a);

    r += b*(1-b)/(2*a);
    r += b*(1-b)*(1-2*b)/(12*a*a);
    r += - b*b*(1-b)*(1-b)/(12*a*a*a);

    return r;
}


/*
 * Special case for a negative integer argument
 */

double beta_negint(int a, double b)
{
    int sgn;
    if (b == boost::numeric_cast<int>(b) && 1 - a - b > 0) {
        sgn = (boost::numeric_cast<int>(b) % 2 == 0) ? 1 : -1;
        return sgn * beta(1 - a - b, b);
    }
    else {
        return INFINITY;
    }
}

double lbeta_negint(int a, double b)
{
    double r;
    if (b == boost::numeric_cast<int>(b) && 1 - a - b > 0) {
        r = lbeta(1 - a - b, b);
        return r;
    }
    else {
        return INFINITY;
    }
}

}
