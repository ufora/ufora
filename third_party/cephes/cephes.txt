



              CEPHES MATHEMATICAL FUNCTION LIBRARY


     This computer software library is a collection of more than
400 high quality mathematical routines for scientific and
engineering applications.   All are written entirely in C
language.  Many of the functions are supplied in six different
arithmetic precisions: 32 bit single (24-bit significand), 64 bit
IEEE double (53-bit), 64 bit DEC (56-bit), 80 or 96 bit IEEE long
double (64-bit), and extended precision formats having 144-bit
and 336-bit significands.  The extended precision arithmetic is
included with the function library.

     The library treats about 180 different mathematical
functions.  In addition to the elementary arithmetic and
transcendental routines, the library includes a substantial
collection of probability integrals, Bessel functions, and higher
transcendental functions.

     There are complex variable routines covering complex
arithmetic, complex logarithm and exponential, and complex
trigonometric functions.

     Each function subroutine has been tested by comparing at a
large number of points against high precision check routines. 
The test programs use floating point arithmetic having 144 bit
(43 decimal) precision.  Thus the actual accuracy of each program
is reported, not merely the result of a consistency test.  Test
results are given with the description of each routine.

     The routines have been characterized and tested in IEEE Std
754 double precision arithmetic (both Intel and Motorola
formats), used on IBM PC and a growing number of other computers,
and also in the popular DEC/IBM double precision format.

     For DEC and IEEE arithmetic, numerical constants and
approximation coefficients are supplied as integer arrays in
order to eliminate conversion errors that might be introduced by
the language compiler.  All coefficients are also supplied in the
normal decimal scientific notation so that the routines can be
compiled and used on other machines that do not support either of
the above numeric formats.

     A single, common error handling routine is supplied.  Error
conditions produce a display of the function name and error type.
The user may easily insert modifications to implement any desired
action on specified types of error.

     The following table summarizes the current contents of the
double precision library.  See also the corresponding
documentation for the single and long double precision libraries.
Accuracies reported for DEC and IEEE arithmetic are with
arithmetic rounding precision limited to 56 and 53 bits,
respectively.  Higher precision may be realized if an arithmetic
unit such as the 8087 or 68881 is used in conjunction with an
optimizing compiler.  The accuracy figures are experimentally
measured; they are not guaranteed maximum errors.

    Documentation is included on the distribution media as
Unix-style manual pages that describe the functions and their
invocation.  The primary documentation for the library functions
is the book by Moshier, Methods and Programs for Mathematical
Functions, Prentice-Hall, 1989.


Function                        Name      Accuracy
--------                        ----    DEC     IEEE
                                        ----    ----
                Arithmetic and Algebraic
Square root                     sqrt    2e-17   2e-16
Long integer square root        lsqrt   1       1
Cube root                       cbrt    2e-17   2e-16
Evaluate polynomial             polevl
Evaluate Chebyshev series       chbevl
Round to nearest integer value  round
Truncate upward to integer      ceil
Truncate downward to integer    floor
Extract exponent                frexp
Add integer to exponent         ldexp
Absolute value                  fabs
Rational arithmetic             euclid
Roots of a polynomial           polrt
Reversion of power series       revers
IEEE 854 arithmetic             ieee
Polynomial arithmetic (polyn.c):
  Add polynomials                 poladd
  Subtract polynomials            polsub
  Multiply polynomials            polmul
  Divide polynomials              poldiv
  Substitute polynomial variable  polsbt
  Evaluate polynomial             poleva
  Set all coefficients to zero    polclr
  Copy coefficients               polmov
  Display coefficients            polprt
 Note, polyr.c contains routines corresponding to
 the above for polynomials with rational coefficients.
Power series manipulations (polmisc.c):
  Square root of a polynomial     polsqt
  Arctangent                      polatn
  Sine                            polsin
Reversion of power series       revers

                Exponential and Trigonometric
Arc cosine                      acos    3e-17   3e-16
Arc hyperbolic cosine           acosh   4e-17   5e-16
Arc hyperbolic sine             asinh   5e-17   4e-16
Arc hyperbolic tangent          atanh   3e-17   2e-16
Arcsine                         asin    6e-17   5e-16
Arctangent                      atan    4e-17   3e-16
Quadrant correct arctangent     atan2   4e-17   4e-16
Cosine                          cos     3e-17   2e-16
Cosine of arg in degrees        cosdg   4e-17   2e-16
Exponential, base e             exp     3e-17   2e-16
Exponential, base 2             exp2    2e-17   2e-16
Exponential, base 10            exp10   3e-17   2e-16
Hyperbolic cosine               cosh    3e-17   3e-16
Hyperbolic sine                 sinh    4e-17   3e-16
Hyperbolic tangent              tanh    3e-17   3e-16
Logarithm, base e               log     2e-17   2e-16
Logarithm, base 2               log2            2e-16
Logarithm, base 10              log10   3e-17   2e-16
Power                           pow     1e-15   2e-14
Integer Power                   powi		9e-14
Sine                            sin     3e-17   2e-16
Sine of arg in degrees          sindg   4e-17   2e-16
Tangent                         tan     4e-17   3e-16
Tangent of arg in degrees       tandg   3e-17   3e-16

                Exponential integral
Exponential integral            expn    2e-16   2e-15
Hyperbolic cosine integral      shichi  9e-17   8e-16
Hyperbolic sine integral        shichi  9e-17   7e-16
Cosine integral                 sici    8e-17A  7e-16
Sine integral                   sici    4e-17A  4e-16

                Gamma
Beta                            beta    8e-15   8e-14
Factorial                       fac     2e-17   2e-15
Gamma                           gamma   1e-16   1e-15
Logarithm of gamma function     lgam    5e-17   5e-16
Incomplete beta integral        incbet  4e-14   4e-13
Inverse beta integral           incbi   3e-13   8e-13
Incomplete gamma integral       igam    5e-15   4e-14
Complemented gamma integral     igamc   3e-15   1e-12
Inverse gamma integral          igami   9e-16   1e-14
Psi (digamma) function          psi     2e-16   1e-15
Reciprocal Gamma                rgamma  1e-16   1e-15

                Error function
Error function                  erf     5e-17   4e-16
Complemented error function     erfc    5e-16   6e-14
Dawson's integral               dawsn   7e-16   7e-16
Fresnel integral (C)            fresnl  2e-16   2e-15
Fresnel integral (S)            fresnl  2e-16   2e-15

                Bessel
Airy (Ai)                       airy    6e-16A  2e-15A
Airy (Ai')                      airy    6e-16A  5e-15A
Airy (Bi)                       airy    6e-16A  4e-15A
Airy (Bi')                      airy    6e-16A  5e-15A
Bessel, order 0                 j0      4e-17A  4e-16A
Bessel, order 1                 j1      4e-17A  3e-16A
Bessel, order n                 jn      7e-17A  2e-15A
Bessel, noninteger order        jv              5e-15A
Bessel, second kind, order 0    y0      7e-17A  1e-15A
Bessel, second kind, order 1    y1      9e-17A  1e-15A
Bessel, second kind, order n    yn      3e-16A  3e-15A
Bessel, noninteger order        yv      see struve.c
Modified Bessel, order 0        i0      8e-17   6e-16
Exponentially scaled i0         i0e     8e-17   5e-16
Modified Bessel, order 1        i1      1e-16   2e-15
Exponentially scaled i1         i1e     1e-16   2e-15
Modified Bessel, nonint. order  iv      3e-15   2e-14
Mod. Bessel, 3rd kind, order 0  k0      1e-16   1e-15
Exponentially scaled k0         k0e     1e-16   1e-15
Mod. Bessel, 3rd kind, order 1  k1      9e-17   1e-15
Exponentially scaled k1         k1e     9e-17   8e-16
Mod. Bessel, 3rd kind, order n  kn      1e-9    2e-8

                Hypergeometric
Confluent hypergeometric        hyperg  1e-15   2e-14
Gauss hypergeometric function   hyp2f1  4e-11   9e-8
2F0                             hyp2f0f  see hyperg.c
1F2                             onef2f   see struve.c
3F0                             threef0f see struve.c

                Elliptic
Complete elliptic integral (E)   ellpe  3e-17   2e-16
Incomplete elliptic integral (E) ellie  2e-16   2e-15
Complete elliptic integral (K)   ellpk  4e-17   3e-16
Incomplete elliptic integral (K) ellik  9e-17   6e-16
Jacobian elliptic function (sn)  ellpj  5e-16A  4e-15A
Jacobian elliptic function (cn)  ellpj          4e-15A
Jacobian elliptic function (dn)  ellpj          1e-12A
Jacobian elliptic function (phi) ellpj          9e-16

                Probability
Binomial distribution           bdtr    4e-14   4e-13
Complemented binomial           bdtrc   4e-14   4e-13
Inverse binomial                bdtri   3e-13   8e-13
Chi square distribution         chdtr   5e-15   3e-14
Complemented Chi square         chdtrc  3e-15   2e-14
Inverse Chi square              chdtri  9e-16   6e-15
F distribution                  fdtr    4e-14   4e-13
Complemented F                  fdtrc   4e-14   4e-13
Inverse F distribution          fdtri   3e-13   8e-13
Gamma distribution              gdtr    5e-15   3e-14
Complemented gamma              gdtrc   3e-15   2e-14
Negative binomial distribution  nbdtr   4e-14   4e-13
Complemented negative binomial  nbdtrc  4e-14   4e-13
Normal distribution             ndtr    2e-15   3e-14
Inverse normal distribution     ndtri   1e-16   7e-16
Poisson distribution            pdtr    3e-15   2e-14
Complemented Poisson            pdtrc   5e-15   3e-14
Inverse Poisson distribution    pdtri   3e-15   5e-14
Student's t distribution        stdtr   2e-15   2e-14

                Miscellaneous
Dilogarithm                     spence  3e-16   4e-15
Riemann Zeta function           zetac   1e-16   1e-15
Two argument zeta function      zeta
Struve function                 struve

                Matrix
Fast Fourier transform          fftr
Simultaneous linear equations   simq
Simultaneous linear equations   gels (symmetric coefficient matrix)
Matrix inversion                minv
Matrix multiply                 mmmpy
Matrix times vector             mvmpy
Matrix transpose                mtransp
Eigenvectors (symmetric matrix) eigens
Levenberg-Marquardt nonlinear equations  lmdif

                Numerical Integration
Simpson's rule                  simpsn
Runge-Kutta                     runge - see de118
Adams-Bashforth                 adams - see de118

                Complex Arithmetic
Complex addition                cadd    1e-17   1e-16
Subtraction                     csub    1e-17   1e-16
Multiplication                  cmul    2e-17   2e-16
Division                        cdiv    5e-17   4e-16
Absolute value                  cabs    3e-17   3e-16
Square root                     csqrt   3e-17   3e-16

        Complex Exponential and Trigonometric
Exponential                     cexp    4e-17   3e-16
Logarithm                       clog    9e-17   5e-16A
Cosine                          ccos    5e-17   4e-16
Arc cosine                      cacos   2e-15   2e-14
Sine                            csin    5e-17   4e-16
Arc sine                        casin   2e-15   2e-14
Tangent                         ctan    7e-17   7e-16
Arc tangent                     catan   1e-16   2e-15
Cotangent                       ccot    7e-17   9e-16

                Applications
Minimax rational approximations to functions    remes
Digital elliptic filters                        ellf
Numerical integration of the Moon and planets   de118
IEEE compliance test for printf(), scanf()      ieetst






                Long Double Precision Functions



Function                        Name    Accuracy
--------                        ----    --------

Arc hyperbolic cosine           acoshl  2e-19
Arc cosine                      acosl   1e-19
Arc hyperbolic sine             asinhl  2e-19
Arcsine                         asinl   3e-19
Arc hyperbolic tangent          atanhl  1e-19
Arctangent                      atanl   1e-19
Quadrant correct arctangent     atan2l  2e-19
Cube root                       cbrtl   7e-20
Truncate upward to integer      ceill
Hyperbolic cosine               coshl   1e-19
Cosine                          cosl    1e-19
Cotangent                       cotl    2e-19
Exponential, base e             expl    1e-19
Exponential, base 2             exp2l   9e-20
Exponential, base 10            exp10l  1e-19
Absolute value                  fabsl
Truncate downward to integer    floorl
Extract exponent                frexpl
Add integer to exponent         ldexpl
Logarithm, base e               logl    9e-20
Logarithm, base 2               log2l   1e-19
Logarithm, base 10              log10l  9e-20
Integer Power                   powil	4e-17
Power                           powl    3e-18
Hyperbolic sine                 sinhl   2e-19
Sine                            sinl    1e-19
Square root                     sqrtl   8e-20
Hyperbolic tangent              tanhl   1e-19
Tangent                         tanl    2e-19








                   Single Precision Routines


Function                        Name    Accuracy
--------                        ----    --------

                Arithmetic

Truncate upward to integer      ceilf
Truncate downward to integer    floorf
Extract exponent                frexpf
Add integer to exponent         ldexpf
Absolute value                  fabsf
Square root                     sqrtf   9e-8
Cube root                       cbrtf   8e-8


           Polynomials and Power Series

Polynomial arithmetic (polynf.c):
  Add polynomials                 poladdf
  Subtract polynomials            polsubf
  Multiply polynomials            polmulf
  Divide polynomials              poldivf
  Substitute polynomial variable  polsbtf
  Evaluate polynomial             polevaf
  Set all coefficients to zero    polclrf
  Copy coefficients               polmovf
  Display coefficients            polprtf
 Note, polyr.c contains routines corresponding to
 the above for polynomials with rational coefficients.
Evaluate polynomial             polevlf (coefficients in reverse order)
Evaluate Chebyshev series       chbevlf (coefficients in reverse order)


                Exponential and Trigonometric
Arc cosine                      acosf   1e-7
Arc hyperbolic cosine           acoshf  2e-7
Arc hyperbolic sine             asinhf  2e-7
Arc hyperbolic tangent          atanhf  1e-7
Arcsine                         asinf   3e-7
Arctangent                      atanf   2e-7
Quadrant correct arctangent     atan2f  2e-7
Cosine                          cosf    1e-7
Cosine of arg in degrees        cosdgf  1e-7
Cotangent                       cotf    3e-7
Cotangent of arg in degrees     cotdgf  2e-7
Exponential, base e             expf    2e-7
Exponential, base 2             exp2f   2e-7
Exponential, base 10            exp10f  1e-7
Hyperbolic cosine               coshf   2e-7
Hyperbolic sine                 sinhf   1e-7
Hyperbolic tangent              tanhf   1e-7
Logarithm, base e               logf    8e-8
Logarithm, base 2               log2f   1e-7
Logarithm, base 10              log10f  1e-7
Power                           powf    1e-6
Integer Power                   powif	1e-6
Sine                            sinf    1e-7
Sine of arg in degrees          sindgf  1e-7
Tangent                         tanf    3e-7
Tangent of arg in degrees       tandgf  2e-7

                Exponential integral

Exponential integral            expnf   6e-7
Hyperbolic cosine integral      shichif 4e-7A
Hyperbolic sine integral        shichif 4e-7
Cosine integral                 sicif   2e-7A
Sine integral                   sicif   4e-7A

                Gamma
Beta                            betaf   4e-5
Factorial                       facf    6e-8
Gamma                           gammaf  6e-7
Logarithm of gamma function     lgamf   7e-7(A)
Incomplete beta integral        incbetf 2e-4
Inverse beta integral           incbif  3e-4
Incomplete gamma integral       igamf   8e-6
Complemented gamma integral     igamcf  8e-6
Inverse gamma integral          igamif  1e-5
Psi (digamma) function          psif    8e-7
Reciprocal Gamma                rgammaf 9e-7

                Error function

Error function                  erff    2e-7
Complemented error function     erfcf   4e-6
Dawson's integral               dawsnf  4e-7
Fresnel integral (C)            fresnlf 1e-6
Fresnel integral (S)            fresnlf 1e-6

                Bessel

Airy (Ai)                       airyf   1e-5A
Airy (Ai')                      airyf   9e-6A
Airy (Bi)                       airyf   2e-6A
Airy (Bi')                      airyf   2e-6A
Bessel, order 0                 j0f     2e-7A
Bessel, order 1                 j1f     2e-7A
Bessel, order n                 jnf     4e-7A
Bessel, noninteger order        jvf     2e-6A
Bessel, second kind, order 0    y0f     2e-7A
Bessel, second kind, order 1    y1f     2e-7A
Bessel, second kind, order n    ynf     2e-6A
Bessel, second kind, order v    yvf     see struvef.c
Modified Bessel, order 0        i0f     4e-7
Exponentially scaled i0         i0ef    4e-7
Modified Bessel, order 1        i1f     2e-6
Exponentially scaled i1         i1ef    2e-6
Modified Bessel, nonint. order  ivf     9e-6
Mod. Bessel, 3rd kind, order 0  k0f     8e-7
Exponentially scaled k0         k0ef    8e-7
Mod. Bessel, 3rd kind, order 1  k1f     5e-7
Exponentially scaled k1         k1ef    5e-7
Mod. Bessel, 3rd kind, order n  knf     2e-4A

                Hypergeometric

Confluent hypergeometric 1F1    hypergf 1e-5
Gauss hypergeometric function   hyp2f1f 2e-3
2F0                             hyp2f0f  see hypergf.c
1F2                             onef2f   see struvef.c
3F0                             threef0f see struvef.c

                Elliptic

Complete elliptic integral (E)   ellpef 1e-7
Incomplete elliptic integral (E) ellief 5e-7
Complete elliptic integral (K)   ellpkf 1e-7
Incomplete elliptic integral (K) ellikf 3e-7
Jacobian elliptic function (sn)  ellpjf 2e-6A
Jacobian elliptic function (cn)  ellpjf 2e-6A
Jacobian elliptic function (dn)  ellpjf 1e-3A
Jacobian elliptic function (phi) ellpjf 4e-7

                Probability

Binomial distribution           bdtrf   7e-5
Complemented binomial           bdtrcf  6e-5
Inverse binomial                bdtrif  4e-5
Chi square distribution         chdtrf  3e-5
Complemented Chi square         chdtrcf 3e-5
Inverse Chi square              chdtrif 2e-5
F distribution                  fdtrf   2e-5
Complemented F                  fdtrcf  7e-5
Inverse F distribution          fdtrif  4e-5A
Gamma distribution              gdtrf   6e-5
Complemented gamma              gdtrcf  9e-5
Negative binomial distribution  nbdtrf  2e-4
Complemented negative binomial  nbdtrcf 1e-4
Normal distribution             ndtrf   2e-5
Inverse normal distribution     ndtrif  4e-7
Poisson distribution            pdtrf   7e-5
Complemented Poisson            pdtrcf  8e-5
Inverse Poisson distribution    pdtrif  9e-6
Student's t distribution        stdtrf  2e-5

                Miscellaneous

Dilogarithm                     spencef 4e-7
Riemann Zeta function           zetacf  6e-7
Two argument zeta function      zetaf   7e-7
Struve function                 struvef 9e-5


                Complex Arithmetic

Complex addition                caddf   6e-8
Subtraction                     csubf   6e-8
Multiplication                  cmulf   1e-7
Division                        cdivf   2e-7
Absolute value                  cabsf   1e-7
Square root                     csqrtf  2e-7

        Complex Exponential and Trigonometric

Exponential                     cexpf   1e-7
Logarithm                       clogf   3e-7A
Cosine                          ccosf   2e-7
Arc cosine                      cacosf  9e-6
Sine                            csinf   2e-7
Arc sine                        casinf  1e-5
Tangent                         ctanf   3e-7
Arc tangent                     catanf  2e-6
Cotangent                       ccotf   4e-7




         QLIB Extended Precision Mathematical Library
 

q100asm.bat    Create 100-decimal Q type library (for IBM PC MSDOS)
q100asm.rsp    

qlibasm.bat    43-decimal Q type library (for IBM PC MSDOS)
qlibasm.rsp    

qlib.lib       Q type library, 43 decimal
qlib100.lib    Q type library, 100 decimal
qlib120.lib    Q type library, 120 decimal


Function calling arguments:
NQ is the number of 16-bit short integers in a number (see qhead.h)
short x[NQ], x1[NQ], ... are inputs
short y[NQ], y1[NQ], ... are outputs

mconf.h        Machine configuration file
mtherr.c       Common error handling routine
qacosh.c       Arc hyperbolic cosine
  qacosh( x, y );
qairy.c        Airy functions
  qairy( x, Ai, Ai', Bi, Bi' );
  Also see source program for auxiliary functions.
qasin.c        Arc sine
  qasin( x, y );
qasinh.c       Arc hyperbolic sine
  qasinh( x, y );
qatanh.c       Arc hyperbolic tangent
  qatanh( x, y );
qatn.c         Arc tangent
  qatn( x, y );
  qatn2( x1, x2, y );  y = radian angle whose tangent is x2/x1
qbeta.c        Beta function
  qbeta( x, y );
qcbrt.c        Cube root
  qcbrt( x, y );
qcmplx.c        Complex variable functions: 
		qcabs	absolute value  qcabs( y );
		qcadd	add
		qcsub	subtract        qcsub( a, b, y );  y = b - a
		qcmul	multiply
		qcdiv	divide          qcdiv( d, n, y );  y = n/d
		qcmov	move
		qcneg	negate          qcneg( y );
		qcexp	exponential function
		qclog	logarithm
		qcsin	sine
		qccos	cosine
		qcasin	arcsine
		qcacos	arccosine
		qcsqrt  square root
		qctan	tangent
		qccot	cotangent
		qcatan	arctangent
qcos.c         Cosine
  qcosm1( x, y );   y = cos(x) - 1
qcosh.c        Hyperbolic cosine
qctst1.c       Universal function test program for complex variables
qdawsn.c       Dawson's integral
qellie.c       Incomplete elliptic integral (E)
qellik.c       Incomplete elliptic integral (K)
qellpe.c       Complete elliptic integral (E)
qellpj.c       Jacobian elliptic functions sn, cn, dn, phi
  qellpj( u, m, sn, cn, dn, phi );  sn = sn(u|m), etc.
qellpk.c       Complete elliptic integral (K)
qerf.c         Error integral
qerfc.c        Complementary error integral
qeuclid.c      Q type rational arithmetic:
			qradd	add fractions
			qrsub	subtract fractions
			qrmul	multiply fractions
			qrdiv	divide fractions
			qreuclid reduce to lowest terms
qexp.c         Exponential function
qexp10.c       Base 10 exponential function
qexp2.c        Base 2 exponential function
qexp21.c       2**x - 1
qexpn.c        Exponential integral
qf68k.a        Q type arithmetic for 68000 OS-9
qf68k.asm      Q type arithmetic for 68000 (Definicon assembler)
qf68k.s        Q type arithmetic for 68000 (System V Unix)
qfac.c         Factorial
qfresf.c       Fresnel integral S(x)
		Fresnel integral C(x)
qgamma.c       Gamma function
		log Gamma function
qhead.asm      Q type configuration file for assembly language
qhead.h        Q type configuration file for C language
qhy2f1.c       Gauss hypergeometric function
qhyp.c         Confluent hypergeometric function
qigam.c        Incomplete gamma integral
qigami.c       Functional inverse of incomplete gamma integral
qin.c          Bessel function In
qincb.c        Incomplete beta integral
qincbi.c       Functional inverse of incomplete beta integral
qine.c         Exponentially weighted In
qjn.c          Bessel function Jv (noninteger order)
		qhank	Hankel's asymptotic expansion
qjypn.c        Auxiliary Bessel functions
qjyqn.c        
qkn.c          modified Bessel function Kn
qkne.c         Exponentially weighted Kn
qlog.c         Natural logarithm
qlog1.c        log(1+x)
qlog10.c       Common logarithm
qndtr.c        Gaussian distribution function
qndtri.c       Functional inverse of Gaussian distribution function
qpolyr.c       Q type polynomial arithmetic, rational coefficients:
			poleva	Evaluate polynomial a(t) at t = x.
			polprt	Print the coefficients of a to D digits.
			polclr	Set a identically equal to zero, up to a[na].
			polmov	Set b = a.
			poladd	c = b + a, nc = max(na,nb)
			polsub	c = b - a, nc = max(na,nb)
			polmul	c = b * a, nc = na+nb
			poldiv	c = b / a, nc = MAXPOL
qpow.c         Power function, also
		qpowi	raise to integer power
qprob.c        Various probability integrals:
			qbdtr	binomial distribution
			qbdtrc  complemented binomial distribution
			qbdtri  inverse of binomial distribution
			qchdtr  chi-square distribution
			qchdti	inverse of chi-square distribution
			qfdtr	F distribution
			qfdtrc	complemented F distribution
			qfdtri	inverse of F distribution
			qgdtr	gamma distribution
			qgdtrc	complemented gamma distribution
			qnbdtr	negative binomial distribution
			qnbdtc	complemented negative binomial
			qpdtr	Poisson distribution
			qpdtrc	complemented Poisson distribution
			qpdtri	inverse of Poisson distribution
qpsi.c         psi function
qshici.c       hyperbolic sine integral
		hyperbolic cosine integral
qsici.c        sine integral
		cosine integral
qsimq.c        solve simultaneous equations
qsin.c         sine
		qsinmx3(x,y); y = sin(x) - x
qsindg.c       sine of arg in degrees
qsinh.obj      hyperbolic sine
qspenc.c       Spence's integral (dilogarithm)
qsqrt.c        square root
qsqrta.c       strictly rounded square root
qstudt.c       Student's t distribution function
qtan.c         tangent
qtanh.c        hyperbolic tangent
qtst1.c        Universal function test program
qyn.c          Bessel function Yn (integer order), also
		qyaux0	auxiliary functions
		qyaux1
		qymod	modulus
		qyphase	phase
qzetac.c       Riemann zeta function


Arithmetic routines

qflt.c         Main Q type arithmetic package:
		asctoq	decimal ASCII string to Q type
		dtoq	DEC double precision to Q type
		etoq	IEEE double precision to Q type
		ltoq	long integer to Q type
		qabs	absolute value
		qadd	add
		qclear	set to zero
		qcmp	compare
		qdiv	divide
		qifrac	long integer part plus q type fraction
		qinfin	set to infinity, leaving its sign alone
		qmov	b = a
		qmul	multiply
		qmuli	multiply by small integer
		qneg	negate
		qnrmlz	adjust exponent and mantissa
		qsub	subtract
		qtoasc	Q type to decimal ASCII string
		qtod	convert Q type to DEC double precision
		qtoe	convert Q type to IEEE double precision
qflta.c        Q type arithmetic, C language loops, strict rounding
qfltb.c        Q type arithmetic, C language faster loops
mulr.asm       Q type multiply, IBM PC assembly language
divn.asm       Q type IBM PC divide routine
subm.asm       Q type assembly language add, subtract for MSDOS
qfltd.asm      Q type arithmetic for 68020 (Definicon assembler)
qconst.c       Q type common constants
qc120.c        120 decimal version of qconst.c
mul128.a       Fast multiply algorithm (for OS-9 68000)
mul128ts.c     Test program for above
mul32.a        
mul64.a        
qfloor.c       Q type floor(), also
		qround() round to integer




                  Applications


calc100.doc    Documentation for 100 digit calculator program
qcalc.c        Command interpreter for calculator program
qcalc.h        Include file for command interpreter
qcalc120.exe   120 decimal calculator program
qcalcasm.bat   Make calculator program
qcalclin.bat   
qccalc.mak     Make complex variable calculator program


qparanoi.c     Paranoia arithmetic test for Q type arithmetic
notes          Paranoia documentation
qparanoi.mak   Paranoia makefile


etst.c         Arithmetic demo program
etstasm.bat    
etstlink.bat   
dentst.c       frexp(), ldexp() tester

qstirling.c    Find coefficients for Stirling's formula

qbernum.c      Generates Bernoulli numbers
qbernum.lst    
qbernuma.bat   

   Calculator programs for qcalc

euler.tak      Euler's constant
gamcof.tak     Bernoulli numbers for gamma function
gamma.tak      Gamma function
lgamnum.doc    Stirling's formula
lgamnum.tak    
zeta.tak       zeta function
ctest.tak      exercise complex variable calculator





A: absolute error; others are relative error (i.e., % of reading)

Copyright 1984 - 1992 by Stephen L. Moshier

Release 1.0: July, 1984
Release 1.1: March, 1985
Release 1.2: May, 1986
Release 2.0: April, 1987
Release 2.1: March, 1989
Release 2.2: July, 1992

