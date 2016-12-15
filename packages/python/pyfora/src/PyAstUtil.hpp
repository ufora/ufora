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

#include "Exceptions.hpp"
#include "PyforaInspect.hpp"
#include "core/PyObjectPtr.hpp"
#include "core/variant.hpp"

#include <memory>
#include <string>
#include <utility>


template<typename... Ts>
struct variant;
class PyforaError;


class PyAstUtil {
public:
    PyAstUtil();

    variant<PyObjectPtr, std::shared_ptr<PyforaError>>
        sourceFilenameAndText(const PyObject*) const;
    variant<long, std::shared_ptr<PyforaError>>
        startingSourceLine(const PyObject*) const;

    PyObject* pyAstFromText(const std::string& fileText) const;
    PyObject* pyAstFromText(const PyObject* pyString) const;
    PyObject* functionDefOrLambdaAtLineNumber(const PyObject* obj,
                                              long sourceLine) const;
    PyObject* classDefAtLineNumber(const PyObject* obj, long sourceLine) const;
    PyObject* withBlockAtLineNumber(const PyObject* obj, long sourceLine) const;
    variant<PyObjectPtr, std::shared_ptr<PyforaError>>
        collectDataMembersSetInInit(PyObject* pyObject) const;

    bool hasReturnInOuterScope(const PyObject* pyAst) const;
    bool hasYieldInOuterScope(const PyObject* pyAst) const;

    long getYieldLocationsInOuterScope(const PyObject* pyAstNode) const;
    long getReturnLocationsInOuterScope(const PyObject* pyAstNode) const;

private:
    void operator=(const PyAstUtil&) = delete;

    std::shared_ptr<PyforaError> translateErrorToCpp() const;

    PyObjectPtr mPyAstUtilModule;
    PyforaInspect mPyforaInspectModule;
    Exceptions mExceptionsModule;
};
