#pragma once

#include <stdint.h>

// TODO preally need to check if Y is modified. ridiculous if it is
extern "C" void svm_train_fora_wrapper(
	const double* X, double* Y, const int64_t* nSamples, const int64_t* nFeatures, 
	const int64_t* kernelType, const int64_t* degree, const double* gamma, const double* coef0, 
	const double* cacheSize, const double* C, const double* tol, const int64_t* shrinking, const int64_t* maxIter,	
	const int64_t* svmTypeIndex, const double* epsilon,
	int64_t* ioNSupportVectors,
	double* ioSupportVectorCoefficients,
	double* ioIntercept,
	int64_t* ioSupportVectorIndices,
	int64_t* ioNSupportVectorsByClass,
	int64_t* ioSupportVectorLabels
	);

extern "C" void svm_predict_fora_wrapper(
	const int64_t* nClasses, const int64_t* nSupportVectors, const double* supportVectorsData,
	double* dualCoefficients, const double* rho, const int64_t* nSupportVectorsByClass,
	const int64_t* supportVectorLabels,
	const double* X, const int64_t* nSamples, const int64_t* nFeatures,
	const int64_t* kernelType, const int64_t* degree, const double* gamma, const double* coef0,
	const double* cacheSize, const double* C, const double* tol, const int64_t* shrinking, const int64_t* maxIter,
	const int64_t* svmTypeIndex, const double* epsilon,
	double* ioPredictedValues
	);


