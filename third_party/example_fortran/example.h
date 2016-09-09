#pragma once

#include <stdint.h>

// these examples are solely used for testing of fora <-> fortran interops

extern "C" void fora_clib_mutate(const double* X, int64_t* i);
extern "C" int64_t fora_clib_noop(const double* X);
