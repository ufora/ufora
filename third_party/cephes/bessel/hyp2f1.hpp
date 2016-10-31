/*
Cephes Math Library Release 2.8:  June, 2000
Copyright 1984, 1987, 1992, 2000 by Stephen L. Moshier
*/

#pragma once

namespace cephes {

double hyt2f1(double a, double b, double c, double x, double *loss);
double hys2f1(double a, double b, double c, double x, double *loss);
double hyp2f1ra(double a, double b, double c, double x, double *loss);
double hyp2f1(double a, double b, double c, double x);

}
