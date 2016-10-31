/*							hyp2f1.c
 *
 *	Gauss hypergeometric function   F
 *	                               2 1
 *
 *
 * SYNOPSIS:
 *
 * double a, b, c, x, y, hyp2f1();
 *
 * y = hyp2f1( a, b, c, x );
 *
 *
 * DESCRIPTION:
 *
 *
 *  hyp2f1( a, b, c, x )  =   F ( a, b; c; x )
 *                           2 1
 *
 *           inf.
 *            -   a(a+1)...(a+k) b(b+1)...(b+k)   k+1
 *   =  1 +   >   -----------------------------  x   .
 *            -         c(c+1)...(c+k) (k+1)!
 *          k = 0
 *
 *  Cases addressed are
 *	Tests and escapes for negative integer a, b, or c
 *	Linear transformation if c - a or c - b negative integer
 *	Special case c = a or c = b
 *	Linear transformation for  x near +1
 *	Transformation for x < -0.5
 *	Psi function expansion if x > 0.5 and c - a - b integer
 *      Conditionally, a recurrence on c to make c-a-b > 0
 *
 * |x| > 1 is rejected.
 *
 * The parameters a, b, c are considered to be integer
 * valued if they are within 1.0e-14 of the nearest integer
 * (1.0e-13 for IEEE arithmetic).
 *
 * ACCURACY:
 *
 *
 *               Relative error (-1 < x < 1):
 * arithmetic   domain     # trials      peak         rms
 *    IEEE      -1,7        230000      1.2e-11     5.2e-14
 *
 * Several special cases also tested with a, b, c in
 * the range -7 to 7.
 *
 * ERROR MESSAGES:
 *
 * A "partial loss of precision" message is printed if
 * the internally estimated relative error exceeds 1^-12.
 * A "singularity" message is printed on overflow or
 * in cases not addressed (such as x < -1).
 */

/*							hyp2f1	*/


/*
Cephes Math Library Release 2.8:  June, 2000
Copyright 1984, 1987, 1992, 2000 by Stephen L. Moshier
*/


#include <cmath>
#include <cassert>
#include <cstdlib>
#include <limits>

#include "psi.hpp"
#include "../consts.hpp"
#include "../gamma.hpp"
#include "hyp2f1.hpp"

namespace cephes {

constexpr int MAX_ITERATIONS = 10000;

double hyp2f1(double a, double b, double c, double x)
    {
    double d, d1, d2, e;
    double p, q, r, s, y, ax;
    double ia, ib, ic, id, err;
    double t1;
    int i, aid;
    int neg_int_a = 0, neg_int_b = 0;
    int neg_int_ca_or_cb = 0;

    err = 0.0;
    ax = std::fabs(x);
    s = 1.0 - x;
    ia = std::round(a);		/* nearest integer to a */
    ib = std::round(b);

    if (x == 0.0) {
        return 1.0;
        }

    d = c - a - b;
    id = std::round(d);

    if ((a == 0 || b == 0) && c != 0) {
        return 1.0;
        }

    if (a <= 0 && std::fabs(a - ia) < EPS) {	/* a is a negative integer */
        neg_int_a = 1;
        }

    if (b <= 0 && std::fabs(b - ib) < EPS) {	/* b is a negative integer */
        neg_int_b = 1;
        }

    if (d <= -1 && !(std::fabs(d - id) > EPS && s < 0)
        && !(neg_int_a || neg_int_b)) {
        return std::pow(s, d) * hyp2f1(c - a, c - b, c, x);
        }
    if (d <= 0 && x == 1 && !(neg_int_a || neg_int_b))
        goto hypdiv;

    if (ax < 1.0 || x == -1.0) {
        /* 2F1(a,b;b;x) = (1-x)**(-a) */
        if (std::fabs(b - c) < EPS) {	/* b = c */
            y = std::pow(s, -a);	/* s to the -a std::power */
            goto hypdon;
            }
        if (std::fabs(a - c) < EPS) {	/* a = c */
            y = std::pow(s, -b);	/* s to the -b std::power */
            goto hypdon;
            }
        }



    if (c <= 0.0) {
        ic = std::round(c);		/* nearest integer to c */
        if (std::fabs(c - ic) < EPS) {	/* c is a negative integer */
            /* check if termination before explosion */
            if (neg_int_a && (ia > ic))
                goto hypok;
            if (neg_int_b && (ib > ic))
                goto hypok;
            goto hypdiv;
            }
        }

    if (neg_int_a || neg_int_b)	/* function is a polynomial */
        goto hypok;

    t1 = std::fabs(b - a);
    if (x < -2.0 && std::fabs(t1 - std::round(t1)) > EPS) {
        /* This transform has a pole for b-a integer, and
         * may produce large cancellation errors for |1/x| close 1
         */
        p = hyp2f1(a, 1 - c + a, 1 - b + a, 1.0 / x);
        q = hyp2f1(b, 1 - c + b, 1 - a + b, 1.0 / x);
        p *= std::pow(-x, -a);
        q *= std::pow(-x, -b);
        t1 = std::tgamma(c);
        s = t1 * std::tgamma(b - a) / (std::tgamma(b) * std::tgamma(c - a));
        y = t1 * std::tgamma(a - b) / (std::tgamma(a) * std::tgamma(c - b));
        return s * p + y * q;
        }
    else if (x < -1.0) {
        if (std::fabs(a) < std::fabs(b)) {
            return std::pow(s, -a) * hyp2f1(a, c - b, c, x / (x - 1));
            }
        else {
            return std::pow(s, -b) * hyp2f1(b, c - a, c, x / (x - 1));
            }
        }

    if (ax > 1.0)		/* series diverges  */
        goto hypdiv;

    p = c - a;
    ia = std::round(p);		/* nearest integer to c-a */
    if ((ia <= 0.0) && (std::fabs(p - ia) < EPS))	/* negative int c - a */
        neg_int_ca_or_cb = 1;

    r = c - b;
    ib = std::round(r);		/* nearest integer to c-b */
    if ((ib <= 0.0) && (std::fabs(r - ib) < EPS))	/* negative int c - b */
        neg_int_ca_or_cb = 1;

    id = std::round(d);		/* nearest integer to d */
    q = std::fabs(d - id);

    /* Thanks to Christian Burger <BURGER@DMRHRZ11.HRZ.Uni-Marburg.DE>
     * for reporting a bug here.  */
    if (std::fabs(ax - 1.0) < EPS) {	/* |x| == 1.0   */
        if (x > 0.0) {
            if (neg_int_ca_or_cb) {
                if (d >= 0.0)
                    goto hypf;
                else
                    goto hypdiv;
                }
            if (d <= 0.0)
                goto hypdiv;
            y = std::tgamma(c) * std::tgamma(d) / (std::tgamma(p) * std::tgamma(r));
            goto hypdon;
            }
        if (d <= -1.0)
            goto hypdiv;
        }

    /* Conditionally make d > 0 by recurrence on c
     * AMS55 #15.2.27
     */
    if (d < 0.0) {
        /* Try the std::power series first */
        y = hyt2f1(a, b, c, x, &err);
        if (err < ETHRESH)
            goto hypdon;
        /* Apply the recurrence if std::power series fails */
        err = 0.0;
        aid = 2 - id;
        e = c + aid;
        d2 = hyp2f1(a, b, e, x);
        d1 = hyp2f1(a, b, e + 1.0, x);
        q = a + b + 1.0;
        for (i = 0; i < aid; i++) {
            r = e - 1.0;
            y = (e * (r - (2.0 * e - q) * x) * d2 +
                (e - a) * (e - b) * x * d1) / (e * r * s);
            e = r;
            d1 = d2;
            d2 = y;
            }
        goto hypdon;
        }


    if (neg_int_ca_or_cb)
        goto hypf;		/* negative integer c-a or c-b */

    hypok:
    y = hyt2f1(a, b, c, x, &err);


    hypdon:
    return (y);

    /* The transformation for c-a or c-b negative integer
     * AMS55 #15.3.3
     */
    hypf:
    y = std::pow(s, d) * hys2f1(c - a, c - b, c, x, &err);
    goto hypdon;

    /* The alarm exit */
    hypdiv:
    return std::numeric_limits<double>::infinity();
    }






/* Apply transformations for |x| near 1
 * then call the std::power series
 */
double hyt2f1(double a, double b, double c, double x, double* loss)
    {
    double p, q, r, s, t, y, w, d, err, err1;
    double ax, id, d1, d2, e, y1;
    int i, aid, sign;

    int ia, ib, neg_int_a = 0, neg_int_b = 0;

    ia = std::round(a);
    ib = std::round(b);

    if (a <= 0 && std::fabs(a - ia) < EPS) {	/* a is a negative integer */
        neg_int_a = 1;
        }

    if (b <= 0 && std::fabs(b - ib) < EPS) {	/* b is a negative integer */
        neg_int_b = 1;
        }

    err = 0.0;
    s = 1.0 - x;
    if (x < -0.5 && !(neg_int_a || neg_int_b)) {
        if (b > a)
            y = std::pow(s, -a) * hys2f1(a, c - b, c, -x / s, &err);

        else
            y = std::pow(s, -b) * hys2f1(c - a, b, c, -x / s, &err);

        goto done;
        }

    d = c - a - b;
    id = std::round(d);		/* nearest integer to d */

    if (x > 0.9 && !(neg_int_a || neg_int_b)) {
        if (std::fabs(d - id) > EPS) {
            int sgngam;

            /* test for integer c-a-b */
            /* Try the std::power series first */
            y = hys2f1(a, b, c, x, &err);
            if (err < ETHRESH)
                goto done;
            /* If std::power series fails, then apply AMS55 #15.3.6 */
            q = hys2f1(a, b, 1.0 - d, s, &err);
            sign = 1;
            w = lgam_sgn(d, &sgngam);
            sign *= sgngam;
            w -= lgam_sgn(c-a, &sgngam);
            sign *= sgngam;
            w -= lgam_sgn(c-b, &sgngam);
            sign *= sgngam;
            q *= sign * exp(w);
            r = std::pow(s, d) * hys2f1(c - a, c - b, d + 1.0, s, &err1);
            sign = 1;
            w = lgam_sgn(-d, &sgngam);
            sign *= sgngam;
            w -= lgam_sgn(a, &sgngam);
            sign *= sgngam;
            w -= lgam_sgn(b, &sgngam);
            sign *= sgngam;
            r *= sign * exp(w);
            y = q + r;

            q = std::fabs(q);	/* estimate cancellation error */
            r = std::fabs(r);
            if (q > r)
                r = q;
            err += err1 + (MACHEP * r) / y;

            y *= std::tgamma(c);
            goto done;
            }
        else {
            /* Psi function expansion, AMS55 #15.3.10, #15.3.11, #15.3.12
             *
             * Although AMS55 does not explicitly state it, this expansion fails
             * for negative integer a or b, since the psi and Std::Tgamma functions
             * involved have poles.
             */

            if (id >= 0.0) {
                e = d;
                d1 = d;
                d2 = 0.0;
                aid = id;
                }
            else {
                e = -d;
                d1 = 0.0;
                d2 = d;
                aid = -id;
                }

            ax = std::log(s);

            /* sum for t = 0 */
            y = psi(1.0) + psi(1.0 + e) - psi(a + d1) - psi(b + d1) - ax;
            y /= std::tgamma(e + 1.0);

            p = (a + d1) * (b + d1) * s / std::tgamma(e + 2.0);	/* Poch for t=1 */
            t = 1.0;
            do {
                r = psi(1.0 + t) + psi(1.0 + t + e) - psi(a + t + d1)
                    - psi(b + t + d1) - ax;
                q = p * r;
                y += q;
                p *= s * (a + t + d1) / (t + 1.0);
                p *= (b + t + d1) / (t + 1.0 + e);
                t += 1.0;
                if (t > MAX_ITERATIONS) {	/* should never happen */
                    *loss = 1.0;
                    return std::numeric_limits<double>::quiet_NaN();
                    }
                }
            while (y == 0 || std::fabs(q / y) > EPS);

            if (id == 0.0) {
                y *= std::tgamma(c) / (std::tgamma(a) * std::tgamma(b));
                goto psidon;
                }

            y1 = 1.0;

            if (aid == 1)
                goto nosum;

            t = 0.0;
            p = 1.0;
            for (i = 1; i < aid; i++) {
                r = 1.0 - e + t;
                p *= s * (a + t + d2) * (b + t + d2) / r;
                t += 1.0;
                p /= t;
                y1 += p;
                }
        nosum:
            p = std::tgamma(c);
            y1 *= std::tgamma(e) * p / (std::tgamma(a + d1) * std::tgamma(b + d1));

            y *= p / (std::tgamma(a + d2) * std::tgamma(b + d2));
            if ((aid & 1) != 0)
                y = -y;

            q = std::pow(s, id);	/* s to the id std::power */
            if (id > 0.0)
                y *= q;
            else
                y1 *= q;

            y += y1;
        psidon:
            goto done;
            }

        }

    /* Use defining std::power series if no special cases */
    y = hys2f1(a, b, c, x, &err);

    done:
    *loss = err;
    return (y);
    }





/* Defining power series expansion of Gauss hypergeometric function */
/* `loss` estimates loss of significance */
double hys2f1(double a, double b, double c, double x, double* loss)
    {
    double f, g, h, k, m, s, u, umax;
    int i;
    int ib, intflag = 0;

    if (std::fabs(b) > std::fabs(a)) {
        /* Ensure that |a| > |b| ... */
        f = b;
        b = a;
        a = f;
        }

    ib = std::round(b);

    if (std::fabs(b - ib) < EPS && ib <= 0 && std::fabs(b) < std::fabs(a)) {
        /* .. except when `b` is a smaller negative integer */
        f = b;
        b = a;
        a = f;
        intflag = 1;
        }

    if ((std::fabs(a) > std::fabs(c) + 1 || intflag) && std::fabs(c - a) > 2
        && std::fabs(a) > 2) {
        /* |a| >> |c| implies that large cancellation error is to be expected.
         *
         * We try to reduce it with the recurrence relations
         */
        return hyp2f1ra(a, b, c, x, loss);
        }

    i = 0;
    umax = 0.0;
    f = a;
    g = b;
    h = c;
    s = 1.0;
    u = 1.0;
    k = 0.0;
    do {
        if (std::fabs(h) < EPS) {
            *loss = 1.0;
            return std::numeric_limits<double>::infinity();
            }
        m = k + 1.0;
        u = u * ((f + k) * (g + k) * x / ((h + k) * m));
        s += u;
        k = std::fabs(u);		/* remember largest term summed */
        if (k > umax)
            umax = k;
        k = m;
        if (++i > MAX_ITERATIONS) {	/* should never happen */
            *loss = 1.0;
            return (s);
            }
        }
    while (s == 0 || std::fabs(u / s) > MACHEP);

    /* return estimated relative error */
    *loss = (MACHEP * umax) / std::fabs(s) + (MACHEP * i);

    return (s);
    }


/*
 * Evaluate hypergeometric function by two-term recurrence in `a`.
 *
 * This avoids some of the loss of precision in the strongly alternating
 * hypergeometric series, and can be used to reduce the `a` and `b` parameters
 * to smaller values.
 *
 * AMS55 #15.2.10
 */
double hyp2f1ra(double a, double b, double c, double x,
		       double *loss)
    {
    double f2, f1, f0;
    int n, da;
    double t, err;

    /* Don't cross c or zero */
    if ((c < 0 && a <= c) || (c >= 0 && a >= c)) {
        da = std::round(a - c);
        }
    else {
        da = std::round(a);
        }
    t = a - da;

    *loss = 0;

    assert(da != 0);

    if (std::abs(da) > MAX_ITERATIONS) {
        /* Too expensive to compute this value, so give up */
        *loss = 1.0;
        return std::numeric_limits<double>::quiet_NaN();
        }

    if (da < 0) {
        /* Recurse down */
        f2 = 0;
        f1 = hys2f1(t, b, c, x, &err);
        *loss += err;
        f0 = hys2f1(t - 1, b, c, x, &err);
        *loss += err;
        t -= 1;
        for (n = 1; n < -da; ++n) {
            f2 = f1;
            f1 = f0;
            f0 = -(2 * t - c - t * x + b * x) / (c - t) * f1 - t * (x -
                1) /
                (c - t) * f2;
            t -= 1;
            }
        }
    else {
        /* Recurse up */
        f2 = 0;
        f1 = hys2f1(t, b, c, x, &err);
        *loss += err;
        f0 = hys2f1(t + 1, b, c, x, &err);
        *loss += err;
        t += 1;
        for (n = 1; n < da; ++n) {
            f2 = f1;
            f1 = f0;
            f0 = -((2 * t - c - t * x + b * x) * f1 +
                (c - t) * f2) / (t * (x - 1));
            t += 1;
            }
        }

    return f0;
    }

}
