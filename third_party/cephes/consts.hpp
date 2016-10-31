/*
Cephes Math Library Release 2.1:  December, 1988
Copyright 1984, 1987, 1988 by Stephen L. Moshier
Direct inquiries to 30 Frost Street, Cambridge, MA 02140
*/

#pragma once

namespace cephes {

// these are taken from the IEEE arithmetic (IBMPC)
// defines in cephes

constexpr double EUL = 0.57721566490153286061;
constexpr double MAXNUM = 1.79769313486231570815E308;
constexpr double PI = 3.14159265358979323846;

constexpr double MACHEP = 1.11022302462515654042E-16; // 2**-53
constexpr double MAXLOG =  7.09782712893383996843E2; // log(2 ** 1024)

constexpr double EPS = 1.0e-13;
constexpr double EPS2 = 1.0e-10;

constexpr double ETHRESH = 1.0e-12;

constexpr double MAXGAM = 171.624376956302725;

constexpr double LOGPI = 1.14472988584940017414;

constexpr double SQTPI = 2.50662827463100050242E0;
}
