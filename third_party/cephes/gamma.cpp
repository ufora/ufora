/*
Cephes Math Library Release 2.3:  December, 1988
Copyright 1984, 1987, 1988 by Stephen L. Moshier
Direct inquiries to 30 Frost Street, Cambridge, MA 02140
*/

#include "consts.hpp"
#include "polevl.hpp"
#include "gamma.hpp"

#include <cmath>
#include <limits>

namespace cephes {

static const double P[] = {
    1.60119522476751861407E-4,
    1.19135147006586384913E-3,
    1.04213797561761569935E-2,
    4.76367800457137231464E-2,
    2.07448227648435975150E-1,
    4.94214826801497100753E-1,
    9.99999999999999996796E-1
};

static const double Q[] = {
    -2.31581873324120129819E-5,
    5.39605580493303397842E-4,
    -4.45641913851797240494E-3,
    1.18139785222060435552E-2,
    3.58236398605498653373E-2,
    -2.34591795718243348568E-1,
    7.14304917030273074085E-2,
    1.00000000000000000320E0
};

/* Stirling's formula for the Gamma function */
static const double STIR[5] = {
    7.87311395793093628397E-4,
    -2.29549961613378126380E-4,
    -2.68132617805781232825E-3,
    3.47222221605458667310E-3,
    8.33333333333482257126E-2,
};

constexpr double MAXSTIR = 143.01608;

/* Gamma function computed by Stirling's formula.
 * The polynomial STIR is valid for 33 <= x <= 172.
 */
double stirf(double x)
    {
    double y, w, v;

    if (x >= MAXGAM) {
        return std::numeric_limits<double>::infinity();
        }
    w = 1.0 / x;
    w = 1.0 + w * polevl(w, STIR, 4);
    y = exp(x);
    if (x > MAXSTIR) {		/* Avoid overflow in pow() */
        v = std::pow(x, 0.5 * x - 0.25);
        y = v * (v / y);
        }
    else {
        y = std::pow(x, x - 0.5) / y;
        }
    y = SQTPI * y * w;
    return (y);
    }


double Gamma(double x)
    {
    double p, q, z;
    int i;
    int sgngam = 1;

    if (!std::isfinite(x)) {
        return x;
        }
    q = std::fabs(x);

    if (q > 33.0) {
        if (x < 0.0) {
            p = std::floor(q);
            if (p == q) {
            gamnan:
                return std::numeric_limits<double>::infinity();
                }
            i = p;
            if ((i & 1) == 0)
                sgngam = -1;
            z = q - p;
            if (z > 0.5) {
                p += 1.0;
                z = q - p;
                }
            z = q * std::sin(PI * z);
            if (z == 0.0) {
                return sgngam * std::numeric_limits<double>::infinity();
                }
            z = std::fabs(z);
            z = PI / (z * stirf(q));
            }
        else {
            z = stirf(x);
            }
        return (sgngam * z);
        }

    z = 1.0;
    while (x >= 3.0) {
        x -= 1.0;
        z *= x;
        }

    while (x < 0.0) {
        if (x > -1.E-9)
            goto small;
        z /= x;
        x += 1.0;
        }

    while (x < 2.0) {
        if (x < 1.e-9)
            goto small;
        z /= x;
        x += 1.0;
        }

    if (x == 2.0)
        return (z);

    x -= 2.0;
    p = polevl(x, P, 6);
    q = polevl(x, Q, 7);
    return (z * p / q);

    small:
    if (x == 0.0) {
        goto gamnan;
        }
    else
        return (z / ((1.0 + 0.5772156649015329 * x) * x));
    }



/* A[]: Stirling's formula expansion of std::log Gamma
 * B[], C[]: std::log Gamma function between 2 and 3
 */
static const double A[] = {
    8.11614167470508450300E-4,
    -5.95061904284301438324E-4,
    7.93650340457716943945E-4,
    -2.77777777730099687205E-3,
    8.33333333333331927722E-2
};

static const double B[] = {
    -1.37825152569120859100E3,
    -3.88016315134637840924E4,
    -3.31612992738871184744E5,
    -1.16237097492762307383E6,
    -1.72173700820839662146E6,
    -8.53555664245765465627E5
};

static const double C[] = {
    /* 1.00000000000000000000E0, */
    -3.51815701436523470549E2,
    -1.70642106651881159223E4,
    -2.20528590553854454839E5,
    -1.13933444367982507207E6,
    -2.53252307177582951285E6,
    -2.01889141433532773231E6
};

/* std::log( sqrt( 2*pi ) ) */
constexpr double LS2PI = 0.91893853320467274178;

constexpr double MAXLGM = 2.556348e305;


/* Logarithm of Gamma function */
double lgam(double x)
    {
    int sign;
    return lgam_sgn(x, &sign);
    }

double lgam_sgn(double x, int *sign)
    {
    double p, q, u, w, z;
    int i;

    *sign = 1;

    if (!std::isfinite(x))
        return x;

    if (x < -34.0) {
        q = -x;
        w = lgam_sgn(q, sign);
        p = std::floor(q);
        if (p == q) {
        lgsing:
            return std::numeric_limits<double>::infinity();
            }
        i = p;
        if ((i & 1) == 0)
            *sign = -1;
        else
            *sign = 1;
        z = q - p;
        if (z > 0.5) {
            p += 1.0;
            z = p - q;
            }
        z = q * std::sin(PI * z);
        if (z == 0.0)
            goto lgsing;
        /*     z = std::log(PI) - std::log( z ) - w; */
        z = LOGPI - std::log(z) - w;
        return (z);
        }

    if (x < 13.0) {
        z = 1.0;
        p = 0.0;
        u = x;
        while (u >= 3.0) {
            p -= 1.0;
            u = x + p;
            z *= u;
            }
        while (u < 2.0) {
            if (u == 0.0)
                goto lgsing;
            z /= u;
            p += 1.0;
            u = x + p;
            }
        if (z < 0.0) {
            *sign = -1;
            z = -z;
            }
        else
            *sign = 1;
        if (u == 2.0)
            return (std::log(z));
        p -= 2.0;
        x = x + p;
        p = x * polevl(x, B, 5) / p1evl(x, C, 6);
        return (std::log(z) + p);
        }

    if (x > MAXLGM) {
        return *sign * std::numeric_limits<double>::infinity();
        }

    q = (x - 0.5) * std::log(x) - x + LS2PI;
    if (x > 1.0e8)
        return (q);

    p = 1.0 / (x * x);
    if (x >= 1000.0)
        q += ((7.9365079365079365079365e-4 * p
                - 2.7777777777777777777778e-3) * p
            + 0.0833333333333333333333) / x;
    else
        q += polevl(p, A, 4) / x;
    return (q);
    }

}
