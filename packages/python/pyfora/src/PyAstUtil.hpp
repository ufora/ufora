/***************************************************************************
   Copyright 2016 Ufora Inc.

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

#include <Python.h>

#include <string>
#include <utility>


class PyAstUtil {
public:
    static PyObject* sourceFilenameAndText(const PyObject*);
    static long startingSourceLine(const PyObject*);

    static PyObject* pyAstFromText(const std::string& fileText);
    static PyObject* pyAstFromText(const PyObject* pyString);
    static PyObject* functionDefOrLambdaAtLineNumber(const PyObject* obj,
                                                     long sourceLine);
    static PyObject* classDefAtLineNumber(const PyObject* obj, long sourceLine);
    static PyObject* withBlockAtLineNumber(const PyObject* obj, long sourceLine);
    static PyObject* collectDataMembersSetInInit(PyObject* pyObject);

    static bool hasReturnInOuterScope(const PyObject* pyAst);
    static bool hasYieldInOuterScope(const PyObject* pyAst);

    static long getYieldLocationsInOuterScope(const PyObject* pyAstNode);
    static long getReturnLocationsInOuterScope(const PyObject* pyAstNode);

private:
    // singleton instance
    static PyAstUtil& _getInstance() {
        static PyAstUtil instance;
        return instance;
        }

    // implement, but keep private for singleton pattern
    PyAstUtil();
    // don't implement for these next two methods for the singleton pattern
    PyAstUtil(const PyAstUtil&);
    void operator=(const PyAstUtil&);

    void _initPyAstUtilModule();
    void _initGetSourceFilenameAndTextFun();
    void _initGetSourceLinesFun();
    void _initPyAstFromTextFun();
    void _initFunctionDefOrLambdaAtLineNumberFun();
    void _initClassDefAtLineNumberFun();

    static void _translateError();

    PyObject* mPyAstUtilModule;
    PyObject* mGetSourceFilenameAndTextFun;
    PyObject* mGetSourceLinesFun;
    PyObject* mPyAstFromTextFun;
    PyObject* mFunctionDefOrLambdaAtLineNumberFun;
    PyObject* mClassDefAtLineNumberFun;
};
