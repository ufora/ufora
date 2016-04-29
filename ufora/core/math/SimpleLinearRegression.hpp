/***************************************************************************
   Copyright 2015 Ufora Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
****************************************************************************/
#pragma once

#include "StatisticsAccumulator.hpp"

/*****************

min(a,b) sum(i)(a x_i + b - y_i)^2

d/da is sum(i) (a x_i + b - y_i) x == 0

d/db is sum(i) (a x_i + b - y_i) == 0

a sum(x^2) + b X - sum(x y) == 0
a X + b - Y == 0

a sum(x^2) + b X == sum(x y)
a X X + b X == Y X

a sum(x^2) - a XX == sum(x y) - Y X
a = (sum(x y) - Y X) / (sum(x^2) - X X)
b = Y - a X

original variance is sum(yy) - Y Y N N
new variance is a^2 sum(x x) + b^2 + sum(yy) + 2 a sum(x) b - 2 b sum(y) - 2 a sum(x y)

imagine we shift x so that sum(x) is zero. that is we have z = x - xbar. Then we know the
new regression is 

    a x + b = a z + (b + a xbar)

so b' is b - a xbar and a' is just a. then the variance is also 

    a^2 sum(z z) + b'^2 + sum(y y) - 2 b' sum(y) - 2 a sum(z y)

sum(z z) = sum((x-xbar)(x-xbar)) = sum(xx) - xbar^2
sum(z y) = sum((x - xbar)y) = sum(x y) - xbar ybar

so then the residual variance is

    a^2 * (sum(xx) - xbar^2) + sum (y y) - 2 b sum(y) - 2 a (sum (xy) - xbar ybar)


*****************/

//a simple 1-dimension OLS regression
class SimpleLinearRegression {
public:
    void observe(double x, double y, double weight = 1.0)
        {
        mX.observe(x,weight);
        mY.observe(y,weight);
        mXY.observe(x * y, weight);
        }

    const StatisticsAccumulator<double, double>& getX() const
        {
        return mX;
        }

    const StatisticsAccumulator<double, double>& getXY() const
        {
        return mXY;
        }

    const StatisticsAccumulator<double, double>& getY() const
        {
        return mY;
        }

    pair<double, double> getParams() const
        {
        double a = (mXY.mean() - mX.mean() * mY.mean()) / (mX.getXX() - mX.mean() * mX.mean());

        if (!boost::math::isfinite(a))
            a = 0.0;

        double b = mY.mean() - a * mX.mean();

        return make_pair(a,b);
        }

    double rSquared() const
        {
        double rv = rawVariance();
        if (rv == 0.0)
        	return 1.0;

        return 1.0 - residualVariance() / rv;
        }

    double rawVariance() const
        {
        return mY.variance();
        }

    double residualVariance() const
        {
        pair<double, double> p = getParams();
        double a = p.first;
        double b = p.second;

        return residualVariance(a,b);
        }

    double residualVariance(double a, double b) const
        {
        double bprime = b + a * mX.mean();

        double sum_zz = mX.getXX() - mX.mean() * mX.mean();
        double sum_zy = mXY.mean() - mX.mean() * mY.mean();

        return a * a * sum_zz + bprime * bprime + mY.getXX() - 2 * bprime * mY.mean() - 2 * a * sum_zy;

        //return a * (a * mX.getXX() - 2 * mXY.mean()) + b * b + mY.getXX() + 
        //    2 * b * (a * mX.mean() - mY.mean());
        }

private:
    StatisticsAccumulator<double, double> mX;
    StatisticsAccumulator<double, double> mY;
    StatisticsAccumulator<double, double> mXY;
};
