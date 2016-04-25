#   Copyright 2016 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


import numpy
import math


from Solver import Solver, ReturnValue


class TrustRegionConjugateGradientSolver(Solver):
    """
    Implements "Trust Region Newton Methods for Large-Scale Logistic Regression"
    of C. Lin, R. Weng, and S. Keerthi 
    (http://www.machinelearning.org/proceedings/icml2007/papers/114.pdf)

    This is the same algorithm used in the liblinear library.
    """
    def __init__(
            self, X, y,
            classZeroLabel,
            C=1.0,
            eps=0.001,
            maxIters=1000,
            splitLimit=1000000):
        self.X = X
        self.y = y
        self.classZeroLabel = classZeroLabel
        self.C = float(C)
        self.eps = TrustRegionConjugateGradientSolver.computeEps(
            eps, y, classZeroLabel)
        self.maxIters = maxIters
        self.nFeatures = X.shape[1]
        self.nSamples = X.shape[0]
        self.splitLimit = splitLimit

        self.eta0 = 1e-4
        self.eta1 = 0.25
        self.eta2 = 0.75

        self.sigma1 = 0.25
        self.sigma2 = 0.5
        self.sigma3 = 4.0

        self.xi = 0.1

    @staticmethod
    def computeEps(eps, y, classZeroLabel):
        def signFunc(elt):
            if elt == classZeroLabel:
                return 1.0
            return 0.0
        numClassZeros = sum(signFunc(elt) for elt in y)
        numClassOnes = len(y) - numClassZeros
        return eps * max(min(numClassZeros, numClassOnes), 1.0) / float(len(y))

    def normalized_y_value(self, ix):
        if self.y[ix] == self.classZeroLabel:
            return 1.0
        return -1.0

    def solve(self, weights=None):
        if weights is None:
            weights = numpy.zeros(self.X.shape[1])

        normGradientAtZeroWeights = self.normGradientAtZeroWeights()

        objectiveFun = ObjectiveFunctionAtWeights(
            self.X,
            self.normalized_y_value,
            self.C,
            weights)

        gradient = objectiveFun.gradient()

        normGradient = self.norm(gradient)
        delta = normGradient

        solverState = SolverState(
            objectiveFun=objectiveFun,
            gradient=gradient,
            normGradient=normGradient,
            delta=delta)

        while solverState.iterationIx < self.maxIters and \
              solverState.normGradient > self.eps * normGradientAtZeroWeights:
            solverState = self.update(solverState)

        return ReturnValue(
            weights=solverState.objectiveFun.w,
            iterations=solverState.iterationIx - 1
            )
        
    def update(self, solverState):
        step, r = self.trustRegionConjugateGradientSearch(
            solverState.objectiveFun,
            solverState.gradient,
            solverState.normGradient,
            solverState.delta)

        candidateObjectiveFun = solverState.objectiveFun.withWeights(
            solverState.objectiveFun.w + step)

        gradientDotStep = solverState.gradient.dot(step)
        estimatedFunctionChange = -0.5 * (gradientDotStep - step.dot(r))
        actualFunctionChange = \
             solverState.objectiveFun.value() - candidateObjectiveFun.value()

        if actualFunctionChange > self.eta0 * estimatedFunctionChange:
            newObjectiveFun = candidateObjectiveFun
            newGradient = candidateObjectiveFun.gradient()
            newNormGradient = self.norm(newGradient)
        else:
            newObjectiveFun = solverState.objectiveFun
            newGradient = solverState.gradient
            newNormGradient = solverState.normGradient

        newDelta = self.updateDelta(
            solverState.delta,
            gradientDotStep,
            solverState.iterationIx,
            step,
            actualFunctionChange,
            estimatedFunctionChange
            )

        return SolverState(
            objectiveFun=newObjectiveFun,
            gradient=newGradient,
            normGradient=newNormGradient,
            delta=newDelta,
            iterationIx=solverState.iterationIx + 1)

    def normGradientAtZeroWeights(self):
        nSamples = len(self.X)
        return math.sqrt(
            sum(
                (-0.5 * self.C * \
                 sum(self.normalized_y_value(ix) * column[ix] for \
                     ix in xrange(nSamples))) ** 2.0 \
                for column in self.X.columns()
                )
            )

    def updateDelta(
            self,
            delta,
            gradientDotStep,
            iterationIx,
            step,
            actualFunctionChange,
            estimatedFunctionChange):
        stepNorm = self.norm(step)

        if iterationIx == 1:
            delta = min(delta, stepNorm)
        
        if -actualFunctionChange - gradientDotStep <= 0:
            alpha = self.sigma3
        else:
            alpha = max(
                self.sigma1,
                -0.5 * (gradientDotStep / \
                        (-actualFunctionChange - gradientDotStep))
                )

        if actualFunctionChange < self.eta0 * estimatedFunctionChange:
            return min(max(alpha, self.sigma1) * stepNorm,
                       self.sigma2 * delta)
        elif actualFunctionChange < self.eta1 * estimatedFunctionChange:
            return max(self.sigma1 * delta,
                       min(alpha * stepNorm, self.sigma2 * delta))
        elif actualFunctionChange < self.eta2 * estimatedFunctionChange:
            return max(self.sigma1 * delta,
                       min(alpha * stepNorm, self.sigma3 * delta))
        else:
            return max(delta,
                       min(alpha * stepNorm, self.sigma3 * delta))
 
    def trustRegionConjugateGradientSearch(
            self,
            objectiveFun,
            gradient,
            normGradient,
            delta):
        step = numpy.zeros(self.nFeatures)
        r = -gradient
        r_norm_squared = r.dot(r)
        d = r
        Hd = objectiveFun.hessian_dot_vec(d)

        iters = 1
        while iters < self.maxIters and \
              math.sqrt(r_norm_squared) > self.xi * normGradient:
            alpha = r_norm_squared / d.dot(Hd)

            step = step + (d * alpha)

            if self.norm(step) >= delta:
                return self.touchedTrustRegion(step, d, alpha, delta, Hd, r)

            r = r - (Hd * alpha)
            old_r_norm_squared = r_norm_squared
            r_norm_squared = r.dot(r)
            
            beta = r_norm_squared / old_r_norm_squared
            d = r + (d * beta)

            Hd = objectiveFun.hessian_dot_vec(d)

        return step, r

    def touchedTrustRegion(self, step, d, alpha, delta, Hd, r):
        step = (d * -alpha) + step
        
        step_dot_d = step.dot(d)
        norm_squared_step = step.dot(step)
        norm_squared_d = d.dot(d)
        deltaSquared = delta * delta
        rad = math.sqrt(step_dot_d * step_dot_d + \
                        norm_squared_d * (deltaSquared - norm_squared_step))
        if step_dot_d >= 0.0:
            alpha = (deltaSquared - norm_squared_step) / (step_dot_d + rad)
        else:
            alpha = (rad - step_dot_d) / norm_squared_d

        step = (d * alpha) + step
        r = (Hd * -alpha) + r

        return step, r

    def norm(self, vec):
        return math.sqrt(vec.dot(vec))


class SolverState(object):
    def __init__(
            self,
            objectiveFun,
            gradient,
            normGradient,
            delta,
            iterationIx=1):
        self.objectiveFun = objectiveFun
        self.gradient = gradient
        self.normGradient = normGradient
        self.delta = delta
        self.iterationIx = iterationIx


class ObjectiveFunctionAtWeights(object):
    def __init__(self, X, normalized_y_value, regularlizer, weights):
        self.X = X
        self.normalized_y_value = normalized_y_value
        self.C = regularlizer
        self.w = numpy.array(weights)
        self.Xw = X.dot(weights)

    def withWeights(self, newWeights):
        return ObjectiveFunctionAtWeights(
            self.X,
            self.normalized_y_value,
            self.C,
            newWeights
            )

    def value(self):
        return 0.5 * self.w.dot(self.w) + self.C * sum(
            math.log(1.0 + math.exp(-self.normalized_y_value(ix) * self.Xw[ix])) \
            for ix in xrange(len(self.Xw))
            )

    def sigma(self, t):
        return 1.0 / (1.0 + math.exp(-t))

    def gradient(self):
        def rowMultiplier(rowIx):
            y_rowIx = self.normalized_y_value(rowIx)
            return (self.sigma(y_rowIx * self.Xw[rowIx]) - 1) * y_rowIx

        rowMultipliers = [rowMultiplier(ix) for ix in xrange(len(self.X))]

        tr = numpy.array(
            [self.C * column.dot(rowMultipliers) for column in self.X.columns()]
            )

        tr = tr + self.w

        return tr

    def hessian_dot_vec(self, v):
        # Hess = I + C * X^t * D * X
        Xv = self.X.dot(v)

        def D_fun(ix):
            sigma = self.sigma(self.normalized_y_value(ix) * self.Xw[ix])
            return sigma * (1 - sigma)

        DXv = [Xv[ix] * D_fun(ix) for ix in xrange(len(Xv))]

        # this part doesn't seem so natural. What if we had a row major self.X?
        tr = numpy.array(
            [self.C * column.dot(DXv) for column in self.X.columns()]
            )

        tr = tr + v

        return tr
