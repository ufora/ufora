/*
  Copyright (c) 2000-2013 Chih-Chung Chang and Chih-Jen Lin
  All rights reserved.

  Redistribution and use in source and binary forms, with or without
  modification, are permitted provided that the following conditions
  are met:

  1. Redistributions of source code must retain the above copyright
  notice, this list of conditions and the following disclaimer.

  2. Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

  3. Neither name of copyright holders nor the names of its contributors
  may be used to endorse or promote products derived from this software
  without specific prior written permission.


  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
  ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
  A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR
  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

/*
  Includes edits by T. Peters:

  1) int replaced with int64_t
  2) remove unnecessary functions, max, min, swap -- instead used std:: versions
  3) use LOG_DEBUG instead of printf

*/

#ifndef _LIBSVM_H
#define _LIBSVM_H

#define LIBSVM_VERSION 317

#ifdef __cplusplus
#include <cstdint>
#else
#include <stdint.h>
#endif
#ifdef __cplusplus
extern "C" {
#endif

	extern const int64_t libsvm_version;

	struct svm_node
		{
		int64_t index;
		double value;
		};

	struct svm_problem
		{
		int64_t l;
		double *y;
		svm_node **x;
		};

	enum { C_SVC, NU_SVC, ONE_CLASS, EPSILON_SVR, NU_SVR };	/* svm_type */
	enum { LINEAR, POLY, RBF, SIGMOID, PRECOMPUTED }; /* kernel_type */

	struct svm_parameter
		{
		int64_t svm_type;
		int64_t kernel_type;
		int64_t degree;	/* for poly */
		double gamma;	/* for poly/rbf/sigmoid */
		double coef0;	/* for poly/sigmoid */

		/* these are for training only */
		double cache_size; /* in MB */
		double eps;	/* stopping criteria */
		double C;	/* for C_SVC, EPSILON_SVR and NU_SVR */
		int64_t nr_weight;		/* for C_SVC */
		int64_t *weight_label;	/* for C_SVC */
		double* weight;		/* for C_SVC */
		double nu;	/* for NU_SVC, ONE_CLASS, and NU_SVR */
		double p;	/* for EPSILON_SVR */
		int64_t shrinking;	/* use the shrinking heuristics */
		int64_t probability; /* do probability estimates */
		};

//
// svm_model
// 
	struct svm_model
		{
		svm_parameter param;	/* parameter */
		int64_t nr_class;		/* number of classes, = 2 in regression/one class svm */
		int64_t l;			/* total #SV */
		svm_node **SV;		/* SVs (SV[l]) */
		double **sv_coef;	/* coefficients for SVs in decision functions (sv_coef[k-1][l]) */
		double *rho;		/* constants in decision functions (rho[k*(k-1)/2]) */
		double *probA;		/* pariwise probability information */
		double *probB;
		int64_t *sv_indices;        /* sv_indices[0,...,nSV-1] are values in [1,...,num_traning_data] to indicate SVs in the training set */

		/* for classification only */

		int64_t *label;		/* label of each class (label[k]) */
		int64_t *nSV;		/* number of SVs for each class (nSV[k]) */
		/* nSV[0] + nSV[1] + ... + nSV[k-1] = l */
		/* XXX */
		int64_t free_sv;		/* 1 if svm_model is created by svm_load_model*/
		/* 0 if svm_model is created by svm_train */
		};

	struct svm_model *svm_train(const svm_problem *prob, const svm_parameter *param);
	void svm_cross_validation(const struct svm_problem *prob, const struct svm_parameter *param, int64_t nr_fold, double *target);

	int64_t svm_get_svm_type(const svm_model *model);
	int64_t svm_get_nr_class(const svm_model *model);
	void svm_get_labels(const svm_model *model, int64_t *label);
	void svm_get_sv_indices(const svm_model *model, int64_t *sv_indices);
	int64_t svm_get_nr_sv(const svm_model *model);
	double svm_get_svr_probability(const svm_model *model);

	double svm_predict_values(const svm_model *model, const svm_node *x, double* dec_values);
	double svm_predict(const struct svm_model *model, const svm_node *x);
	double svm_predict_probability(const svm_model *model, const svm_node *x, double* prob_estimates);

	void svm_free_model_content(svm_model *model_ptr);
	void svm_free_and_destroy_model(svm_model **model_ptr_ptr);
	void svm_destroy_param(struct svm_parameter *param);

	const char *svm_check_parameter(const svm_problem *prob, const svm_parameter *param);
	int64_t svm_check_probability_model(const svm_model *model);

	void svm_set_print_string_function(void (*print_func)(const char *));

#ifdef __cplusplus
	}
#endif

#endif /* _LIBSVM_H */
