#   Copyright 2015 Ufora Inc.
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

import scipy
import scipy.sparse
import scipy.sparse.linalg
from scipy.sparse.linalg import lobpcg
import numpy
import time
import math

import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import matplotlib.pyplot as plt
import numpy.random

numpy.random.seed(1)


lil_matrix = scipy.sparse.lil_matrix

cols = 2
rows = 500

setupT0 = time.time()

pageNeighborhoods = {}

def page(r,c):
	return "p_%s_%s" % (r,c)

pageNeighborhoods[page(-1,-1)] = []
for r in range(rows):
	for c in range(cols):
		pageNeighborhoods[page(r,c)] = []

neighborhoods = []
neighborhoodToIndex = {}
neighborhoodPages = {}

def neighborhood(pages):
	return "n_" + "_".join(pages)



for r in range(rows):
	for c1 in range(cols):
		for c2 in range(cols):
			pageList = [page(r,c1),page(r,c2),page( (r+1) % rows,c1),page( (r+1) % rows,c2)]
			n = neighborhood(pageList)

			neighborhoods.append(n)
			neighborhoodToIndex[n] = len(neighborhoods)-1
			neighborhoodPages[n] = pageList

			for p in pageList:
				pageNeighborhoods[p].append(n)

if 0:
	for c in range(cols-1):
		for r1 in range(rows):
			for r2 in range(rows):
				if c+1 < cols:
					pageList = [page(r1,c),page(r2,c),page(r1,c+1),page(r2,c+1)]
					n = neighborhood(pageList)

					neighborhoods.append(n)
					neighborhoodToIndex[n] = len(neighborhoods)-1
					neighborhoodPages[n] = pageList

					for p in pageList:
						pageNeighborhoods[p].append(n)

print "total of ", len(neighborhoods), " neighborhoods"

def adjacentNeighborhoods(neighborhood):
	res = set()
	for p in neighborhoodPages[neighborhood]:
		for other in pageNeighborhoods[p]:
			res.add(other)
	return res



def add(A, D, n1, n2, w):
	n1Ix = neighborhoodToIndex[n1]
	n2Ix = neighborhoodToIndex[n2]
	A[(n1Ix, n2Ix)] += -1.0 * w
	A[(n2Ix, n1Ix)] += -1.0 * w
	D[(n1Ix, n1Ix)] += w
	D[(n2Ix, n2Ix)] += w

def randomPairs(count, toKeep):
	total = count * (count-1)/2

	if total==toKeep:
		allPairs = []
		for ix in range(count):
			for ix2 in range(count):
				if (ix < ix2):
					allPairs.append((ix, ix2))
		return allPairs

	if toKeep >= total / 2:
		allPairs = []
		for ix in range(count):
			for ix2 in range(count):
				if (ix < ix2):
					allPairs.append((ix, ix2))

		numpy.random.shuffle(allPairs)

		return allPairs[:toKeep]
	else:
		#we have to do this via sampling
		allPairs = set()
		while len(allPairs) < toKeep:
			ix1 = int(numpy.random.rand() * count)
			ix2 = int(numpy.random.rand() * count)
			if ix1 < ix2 and (ix1,ix2) not in allPairs:
				allPairs.add((ix1,ix2))

		allPairs = list(allPairs)
		return allPairs



#construct the laplacian
def constructNeighborhoodwise(A,D, countPerNeighborhood=20):
	ct = 0
	for n1 in neighborhoods:
		ct += 1
		if ct % 10000 == 0:
			print ct,"/",len(neighborhoods)

		for ix in range(countPerNeighborhood):
			pages = neighborhoodPages[n1]
			p = pages[int(len(pages)*numpy.random.rand())]

			others = pageNeighborhoods[p]
			n2 = others[int(len(others) * numpy.random.rand())]

			add(A, D, n1,n2,1)

#construct pairwise
def constructPagewise(A,D):
	pageCount = 0
	for p in pageNeighborhoods:
		pageCount += 1
		if pageCount % 10 == 0:
			print pageCount, "/", len(pageNeighborhoods)
		if len(pageNeighborhoods[p]) > 1:
			count = len(pageNeighborhoods[p])

			pairCount = count * (count-1)/2

			numToKeep = min(1000,pairCount)
			
			allPairs = randomPairs(count, numToKeep)

			allPairs = [(pageNeighborhoods[p][ix],pageNeighborhoods[p][ix2]) for (ix,ix2) in allPairs]

			assert len(allPairs) == numToKeep, (len(allPairs),numToKeep)

			#intended weight
			w = 1.0 / pairCount

			#fraction to keep
			actualW = 1.0#1.0 / pairCount #1#w * pairCount / float(numToKeep)

			for n1,n2 in allPairs:
				add(A, D, n1,n2,actualW)

A = scipy.sparse.dok_matrix((len(neighborhoods),len(neighborhoods)))
D = scipy.sparse.dok_matrix((len(neighborhoods),len(neighborhoods)))

constructNeighborhoodwise(A,D, 5)

def norm2(*args):
	if len(args) == 1:
		x = args[0]
	else:
		x = args[1] - args[0]
	return ((x*x)**.5).sum()

def flip(x):
	if x[:len(x)/2].sum() < 0.0:
		return x[::-1]
	return x



def solveEigenspace(x, m = 2):
	k = numpy.random.uniform(.5, 1.0, (len(neighborhoods),m))

	for ix in range(20):
		t0 = time.time()
		res = lobpcg(x,k,largest=False,maxiter=50)
		
		k = res[1]

	return res

def solveAndPlotEigenspace(A,D,m=2):
	x = A+D
	x = x.tocsr()

	res = solveEigenspace(x,m)

	if m >= 3:
		fig = plt.figure()
		ax = fig.gca(projection='3d')

		ct = len(res[1][:,0])
		slices = 4;
		per = ct / slices
		for ix in range(slices):
			ax.plot(
				res[1][ix*per:(ix+1)*per,0], 
				res[1][ix*per:(ix+1)*per,1], 
				res[1][ix*per:(ix+1)*per,2]
				)
		
		plt.show()

	for ix in range(m):
		plt.plot(res[1][:,ix],label="Eigenvalue %s=%s" % (ix,res[0][ix]))

		v = res[1][:,ix]

		print v.dot(x.dot(v))

		plt.legend()
		plt.show()

def normalizeAndDemean(x):
	x = x - x.sum() / len(x)
	return x / ((x*x).sum())**.5


def updateByAveraging(A, D, x):
	averages = A.dot(x)[:,0]

	x2 = D * averages

	x = normalizeAndDemean(x2)

	x = x.reshape((len(x),1))

	return x


def error(AD, x):
	ADx = AD.dot(x)
	l = x.T.dot(ADx)[0,0]

	r = ADx - l * x

	return r.T.dot(r)[0,0] ** .5


def updateByAveragingAndStepping(A, D, x):
	x2 = updateByAveraging(A, D, x)
	x3 = updateByAveraging(A, D, x2)
	x4 = updateByAveraging(A, D, x3)

	o1 = x2 - x
	o2 = x3 - x2
	o3 = x4 - x3

	if (o1 * o1).sum() ** .5 > .25:
		return x3

	b = (3 * o1 - o2) / 2
	a = (o2-o1) / 2

	#estimate our error
	def positionForT(t):
		return normalizeAndDemean(x + t * t * a + t * b)

	estimatedX4 = positionForT(3)
	estimatedO3 = estimatedX4 - x3

	errRate = norm2(estimatedO3 - o3) / norm2(o3)

	optimalSteps = (1.0 / errRate) ** .5

	if optimalSteps < 4:
		return x4

	candidate = updateByAveraging(A, D, positionForT(optimalSteps))

	return candidate
	
def updateSingleLOBPCG(AD, x):
	x = normalizeAndDemean(x)
	ADx = AD.dot(x)
	l = x.T.dot(ADx)[0,0]

	r = ADx - l * x

	rMean = r.T.dot(r)[0,0] ** .5

	r = normalizeAndDemean(r)

	#r,x are both orthogonal to 1
	ADr = AD.dot(r)
	rADr = r.T.dot(ADr)[0,0]
	xADr = x.T.dot(ADr)[0,0]

	#we have the matrix [[l,xADr],[xADr,rADr]]. compute its eigenvalues explicitly
	#http://www.math.harvard.edu/archive/21b_fall_04/exhibits/2dmatrices/index.html

	T = l + rADr
	D = l * rADr - xADr * xADr

	eigenval = T/2 - (T*T / 4 - D) ** .5
	eigenvalLarge = T/2 + (T*T / 4 - D) ** .5

	if xADr != 0.0:
		eigenvec = [eigenval-rADr,xADr]
	else:
		eigenvec = [0.0,1.0]

	return normalizeAndDemean(x * eigenvec[0] + r * eigenvec[1])
	
def dFromA(A):
	return (-1.0 / A.sum(1)).getA().reshape(A.shape[0])

def optimizeGroups(A,D,x,groups):
	V = lil_matrix((len(x),len(groups)))
	for ix in range(len(groups)):
		V[groups[ix],ix] = 1.0

	Areduced = lil_matrix((len(groups),len(groups)))
	for ix in range(len(groups)):
		Areduced[ix,ix] = 0.0

	Areduced = V.T * A * V
	Areduced = Areduced.tocsr()

	Dreduced = dFromA(Areduced)

	xreduced = normalizeAndDemean( (V.T * x.reshape((len(x),1))) )
	xreducedOrig = xreduced

	for ix in range(1000):
		xreduced = updateByAveraging(Areduced,Dreduced,xreduced)

	xReverse = normalizeAndDemean(V * xreduced.reshape((len(xreduced),1)))

	xOrigReverse = normalizeAndDemean(V * xreducedOrig.reshape((len(xreducedOrig),1)))

	return xReverse # normalizeAndDemean( x + (xReverse - xOrigReverse) )


def updateByAveragingOrthogonal(A, D, x, *basis):
	averages = A.dot(x)[:,0]
	x2 = D * averages

	for b in basis:
		ip = b.T.dot(x2)[0]
		x2 = x2 - ip * b.reshape(len(x))

	x2 = normalizeAndDemean(x2)

	return x2.reshape((len(x),1))



def solveUsingAveragingOrthogonal(AOrig, DOrig):
	A = AOrig.tocsr()
	D = -1.0 / DOrig.diagonal()

	x = numpy.random.uniform(0, 1.0, (len(neighborhoods), 1))
	x = normalizeAndDemean(x)

	x2 = numpy.random.uniform(0, 1.0, (len(neighborhoods), 1))
	x2 = normalizeAndDemean(x2)

	x3 = numpy.random.uniform(0, 1.0, (len(neighborhoods), 1))
	x3 = normalizeAndDemean(x3)

	for ix in range(40):
		for ix2 in range(100):
			x = updateByAveragingAndStepping(A,D,x)
			x2 = updateByAveragingOrthogonal(A,D,x2, x)
			x3 = updateByAveragingOrthogonal(A,D,x3, x, x2)

		fig = plt.figure()
		ax = fig.gca(projection='3d')
		ax.plot(x.reshape(len(x)), x2.reshape(len(x)), x3.reshape(len(x)))
		plt.show()




def solveUsingBlockAveraging(AOrig, DOrig):
	A = AOrig.tocsr()
	D = -1.0 / DOrig.diagonal()

	x = numpy.random.uniform(0, 1.0, (len(neighborhoods), 1))
	x = normalizeAndDemean(x)

	def subdivide(A, D, x, maxGroupSize, meanings=None):
		if len(x) == 0:
			return []

		if meanings is None:
			meanings = range(len(x))

		if len(x) < maxGroupSize * 8:
			x = numpy.random.uniform(0, 1.0, (len(x), 1))
			x = normalizeAndDemean(x)

			for ix in range(200):
				x = updateByAveragingAndStepping(A, D, x)

		#divide into pieces and return a list of lists of indices

		if len(x) < maxGroupSize:
			l = []
			r = []
			for ix in range(len(x)):
				if x[ix] > 0.0:
					l.append(meanings[ix])
				else:
					r.append(meanings[ix])
			if not l:
				return [r]
			if not r:
				return [l]

			return [l,r]

		cut = sorted(x)[len(x)/2]
		indicesL = (x>cut).reshape(len(x))
		indicesR = (x<=cut).reshape(len(x))
		
		AL = A[:,indicesL]
		AL = AL[indicesL,:]
		DL = dFromA(AL)

		AR = A[:,indicesR]
		AR = AR[indicesR,:]
		DR = dFromA(AR)


		if len(DL) == 0 or len(DR) == 0:
			return [meanings]

		l = subdivide(AL,DL,x[indicesL],maxGroupSize,[meanings[ix] for ix in range(len(x)) if indicesL[ix]])
		r = subdivide(AR,DR,x[indicesR],maxGroupSize,[meanings[ix] for ix in range(len(x)) if indicesR[ix]])

		return l+r

	x0 = x

	for ix in range(1000):
		x0 = updateByAveragingAndStepping(A,D,x0)

	for ix in range(100):
		x = updateByAveragingAndStepping(A,D,x)

	groups = sorted(subdivide(A,D,x,30), key=lambda g: g[0])
	x2 = optimizeGroups(A,D,x,groups)

	x3 = x2
	for ix in range(100):
		x3 = updateByAveragingAndStepping(A,D,x3)

	groups = sorted(subdivide(A,D,x3,30), key=lambda g: g[0])
	x4 = optimizeGroups(A,D,x3,groups)
	
	for ix in range(100):
		x4 = updateByAveragingAndStepping(A,D,x4)


	plt.plot(x0,label="just iteration")
	plt.plot(x,label="pre-groups")
	plt.plot(x3,label="post groups")
	plt.plot(x4,label="post groups 2")

	plt.legend()

	plt.show()



def solveSimply(AOrig,DOrig):
	AD = (AOrig+DOrig).tocsr()
	A = AOrig.tocsr()
	D = -1.0 / DOrig.diagonal()


	x = numpy.random.uniform(0, 1.0, (len(neighborhoods), 1))
	x = normalizeAndDemean(x)

	xSimple = x
	
	errors = []
	separation = []

	def sep(x):
		low = x[:len(neighborhoods)/2,0]
		high = x[len(neighborhoods)/2:,0]

		return abs((high.mean() - low.mean())/numpy.std(x))
		

	elapsed = 0.0
	elapsedSimple = 0.0
	for passIx in range(10):
		t0 = time.time()
		for ix in range(400):
			x = updateSingleLOBPCG(AD, x)
		elapsed += time.time() - t0

		t0 = time.time()
		for ix in range(100):
			xSimple = updateByAveragingAndStepping(A, D, xSimple)

		elapsedSimple += time.time() - t0

		print "LOBPCG-2 method: ", elapsed, " with error ", error(AD, x)
		print "Simple method:   ", elapsedSimple, " with error ", error(AD, xSimple)

	eigenT0 = time.time()
	eigenstyle = flip(solveEigenspace(AD,2)[1][:,1].reshape((len(neighborhoods),1)))
	eigenElapsed = time.time() - eigenT0
	print "Eigen: ", eigenElapsed, " with error ", error(AD, eigenstyle)


	plt.plot(flip(x),label="lobpcg-2")
	plt.plot(flip(xSimple),label="averaging")
	plt.plot(eigenstyle,label="eigenvector")
	plt.legend()
	plt.show()


solveUsingAveragingOrthogonal(A,D)


