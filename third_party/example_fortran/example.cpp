#include "example.h"

void fora_clib_mutate(const double* X, int64_t* i)
	{
	*i = *i + 1;
	};

int64_t fora_clib_noop(const double* X) { return 0; }
