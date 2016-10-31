#pragma once

extern "C" double ufora_strtod(const char *s00, char **se);
extern "C" char *ufora_dtoa(double d, int mode, int ndigits,
			int *decpt, int *sign, char **rve);
extern "C" void ufora_freedtoa(char* c);
