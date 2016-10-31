#include "libsvm_fora_helpers.h"
#include "svm.h"
#include <iostream>
#include <vector>

namespace {

	// stupid that y has to be non const here ... should hack svm.h
	void set_problem(
		svm_problem* problem, const double* X, double* Y,
		int64_t nSamples, int64_t nFeatures
		);

	void set_parameter(
		svm_parameter* parameter, int64_t kernelType, int64_t degree, double gamma,
		double coef0, double cacheSize, double C, double tol, int64_t shrinking,
		int64_t maxIter, int64_t svmTypeIndex, double epsilon
		);

	void set_model(
		svm_model* model, const svm_parameter&, int64_t nClasses,
		int64_t nSupportVectors, int64_t nFeatures, const double* supportVectorsData,
		double* dualCoefficients, const double* rho,
		const int64_t* supportVectorLabels, const int64_t* nSupportVectorsByClass
		);

	void getNSupportVectorsByClass(int64_t* ioNSupportVectorsByClass, const svm_model* model);
	void getSupportVectorCoefficients(double* ioSupportVectorCoefficients, const svm_model*);
	void getSupportVectorIndices(int64_t* ioSupportVectorIndices, const svm_model*);
	void getIntercept(double* ioIntercept, const svm_model*);
	void getSupportVectorLabels(int64_t* ioSupportVectorLabels, const svm_model*);

	void free_problem(svm_problem* problem);
	void free_model(svm_model* model);

	svm_node** dense_to_libsvm(const double* X, int64_t nSamples, int64_t nFeatures);

	template<class T>
	void print_array(const T* t, int64_t sz)
		{
		std::cout << "[";
		for (int64_t ix = 0; ix < sz; ++ix)
			{
			std::cout << t[ix];
			if (ix != sz - 1)
				std::cout << ", ";
			}
		std::cout << "]\n";
		}

	}


extern "C" {

	void svm_predict_fora_wrapper(
			const int64_t* nClasses, const int64_t* nSupportVectors, const double* supportVectorsData,
			double* dualCoefficients, const double* rho, const int64_t* nSupportVectorsByClass,
			const int64_t* supportVectorLabels,
			const double* X, const int64_t* nSamples, const int64_t* nFeatures,
			const int64_t* kernelType, const int64_t* degree, const double* gamma, const double* coef0,
			const double* cacheSize, const double* C, const double* tol, const int64_t* shrinking, const int64_t* maxIter,
			const int64_t* svmTypeIndex, const double* epsilon,
			double* ioPredictedValues
			)
		{
		svm_parameter parameter;

		set_parameter(
		 	&parameter, *kernelType, *degree, *gamma,
		 	*coef0, *cacheSize, *C, *tol, *shrinking,
		 	*maxIter, *svmTypeIndex, *epsilon
			);

		svm_model model;

		set_model(
		  	&model,
		  	parameter, *nClasses, *nSupportVectors, *nFeatures,
		  	supportVectorsData, dualCoefficients,
		  	rho, supportVectorLabels,
		  	nSupportVectorsByClass
		  	);

		svm_node** XAsSvmNode = dense_to_libsvm(X, *nSamples, *nFeatures);

		for (int64_t ix = 0; ix < *nSamples; ++ix)
			ioPredictedValues[ix] = svm_predict(&model, XAsSvmNode[ix]);

		free(XAsSvmNode[0]);
		free(XAsSvmNode);
		free_model(&model);
		}

	void svm_train_fora_wrapper(
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
			)
		{
		svm_problem problem;
		svm_parameter parameter;

		set_problem(
			&problem, X, Y,
			*nSamples, *nFeatures
			);

		set_parameter(
		 	&parameter, *kernelType, *degree, *gamma,
		 	*coef0, *cacheSize, *C, *tol, *shrinking,
		 	*maxIter, *svmTypeIndex, *epsilon
			);

		svm_model* model = svm_train(&problem, &parameter);

		*ioNSupportVectors = model->l;
		getSupportVectorCoefficients(ioSupportVectorCoefficients, model);
		getIntercept(ioIntercept, model);
		getSupportVectorIndices(ioSupportVectorIndices, model);
		getNSupportVectorsByClass(ioNSupportVectorsByClass, model);

		if (*svmTypeIndex != EPSILON_SVR and
			*svmTypeIndex != ONE_CLASS and
			*svmTypeIndex != NU_SVR)
			getSupportVectorLabels(ioSupportVectorLabels, model);

		svm_free_and_destroy_model(&model);
		free_problem(&problem);
		}

	}

namespace {

	void set_problem(
			svm_problem* problem, const double* X, double* Y,
			int64_t nSamples, int64_t nFeatures
			)
		{
		problem->l = nSamples;
		problem->y = Y;
		problem->x = dense_to_libsvm(X, nSamples, nFeatures);
		}

	void free_problem(svm_problem* problem)
		{
		free(*problem->x);
		free(problem->x);
		}

	void free_model(svm_model* model)
		{
		/* malloc'ing happens in dense_to_libsvm, called within set_model */
		free(model->SV[0]);
		free(model->SV);

		free(model->sv_coef);

		free(model->rho);
		free(model->label);
		free(model->nSV);
		}

	void set_model(
 	 		svm_model* model,
			const svm_parameter& param, int64_t nClasses, int64_t nSupportVectors, int64_t nFeatures,
			const double* supportVectorsData, double* dualCoefficients,
			const double* rho, const int64_t* supportVectorLabels,
			const int64_t* nSupportVectorsByClass
			)
		{
		// TODO handle NULL ret values from malloc

		model->param = param;
		model->nr_class = nClasses;
		model->l = nSupportVectors;
		model->SV = dense_to_libsvm(supportVectorsData, nSupportVectors, nFeatures);

		model->sv_coef = (double**) malloc((nClasses - 1) * sizeof(double*));
		if (model->sv_coef == NULL) printf("sv_coef NULL!!!\n");
		for (int64_t ix = 0; ix < nClasses - 1; ++ix)
			model->sv_coef[ix] = dualCoefficients + ix * nSupportVectors;

		int64_t m = (nClasses * (nClasses - 1) / 2);

		model->rho = (double*) malloc(m * sizeof(double));
		if (model->rho == NULL) printf("rho is NULL!!\n");
		for (int64_t ix = 0; ix < m; ++ix)
			(model->rho)[ix] = -rho[ix];

		model->probA = NULL;
		model->probB = NULL;
		model->sv_indices = NULL;

		if (param.svm_type == EPSILON_SVR or
			param.svm_type == ONE_CLASS or
			param.svm_type == NU_SVR)
			{
			model->label = NULL;
			model->nSV = NULL;
			}
		else {
			model->label = (int64_t*) malloc(nClasses * sizeof(int64_t));
			if (model->label == NULL) printf("NULL label!\n");
			memcpy(model->label, supportVectorLabels, nClasses * sizeof(int64_t));

			model->nSV = (int64_t*) malloc(nClasses * sizeof(int64_t));
			if (model->nSV == NULL) printf("NULL nSV!!!!\n");
			memcpy(model->nSV, nSupportVectorsByClass, nClasses * sizeof(int64_t));
			}

		model->free_sv = 1;
		}

	void set_parameter(
			svm_parameter* parameter, int64_t kernelType, int64_t degree, double gamma,
			double coef0, double cacheSize, double C, double tol, int64_t shrinking,
			int64_t maxIter, int64_t svmTypeIndex, double epsilon
			)
		{
		parameter->svm_type = svmTypeIndex; // defined in svm.h
		parameter->kernel_type = kernelType;
		parameter->degree = degree;
		parameter->coef0 = coef0;
		parameter->gamma = gamma;

		parameter->cache_size = cacheSize;
		parameter->eps = tol; // this is the tol arg (in Fora-land) which sets convergence tolerance.
		parameter->C = C;
		parameter->nr_weight = 0;
		parameter->weight_label = NULL;
		parameter->weight = NULL;
		parameter->nu = 0.0; // not used for C_SVC
		parameter->p = epsilon;  // yep, names suck. this is used for SVR, NOT related to convergence cond.
		parameter->shrinking = shrinking;
		parameter->probability = (int64_t) 0;  // we cannot do probabilities since they use rand

		// we should add this to libsvm, as in scikit
		//parameter->max_iter = maxIter;
		}

	svm_node** dense_to_libsvm(const double* X, int64_t nSamples, int64_t nFeatures)
		{
		svm_node** svm_node_ptr_ptr = (svm_node**) malloc(sizeof(svm_node*) * nSamples);

		if (svm_node_ptr_ptr == NULL) printf("svm_node_ptr_ptr NULL!!\n");

		svm_node* svm_node_ptr = (svm_node*) malloc(sizeof(svm_node) * nSamples * (nFeatures + 1));

		if (svm_node_ptr == NULL) printf("svm_node_ptr NULL!!\n");

		int64_t ix = (int64_t) 0;
		for (int64_t sampleIx = 0; sampleIx < nSamples; ++sampleIx)
			{
			svm_node_ptr_ptr[sampleIx] = svm_node_ptr;

			for (int64_t featureIx = 0; featureIx < nFeatures; ++featureIx)
				{
				svm_node_ptr->index = featureIx + 1;
				svm_node_ptr->value = X[ix];

				++svm_node_ptr;
				++ix;
				}

			svm_node_ptr->index = -1;
			svm_node_ptr->value = 0.0;

			++svm_node_ptr;
			}

		return svm_node_ptr_ptr;
		}

	void getNSupportVectorsByClass(int64_t* ioNSupportVectorsByClass, const svm_model* model)
		{
		if (model->label == NULL)
			return;

		memcpy(ioNSupportVectorsByClass, model->nSV, model->nr_class * sizeof(int64_t));
		}

	void getSupportVectorCoefficients(double* supportVectorCoefficients, const svm_model* model)
		{
		int64_t k = model->nr_class - 1;

		for (int64_t ix = 0; ix < k; ++ix)
			{
			memcpy(supportVectorCoefficients, model->sv_coef[ix], sizeof(double) * model->l);
			supportVectorCoefficients += model->l;
			}
		}

	void getSupportVectorIndices(int64_t* ioSupportVectorIndices, const svm_model* model)
		{
		memcpy(ioSupportVectorIndices, model->sv_indices, model->l * sizeof(int64_t));
		}

	void getSupportVectorLabels(int64_t* ioSupportVectorLabels, const svm_model* model)
		{
		memcpy(ioSupportVectorLabels, model->label, model->nr_class * sizeof(int64_t));
		}

	void getIntercept(double* ioIntercept, const svm_model* model)
		{
		int64_t n = model->nr_class * (model->nr_class - 1) / 2;
		double t;

		for (int64_t ix = 0; ix < n; ++ix)
			{
			t = model->rho[ix];

			*ioIntercept = (t != 0) ? -t : 0;
			++ioIntercept;
			}
		}

	}

