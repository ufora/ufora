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

#include "../PyObjectUtils.hpp"
#include "../core/PyObjectPtr.hpp"

#include <stdexcept>
#include <string>


class PyforaError : public std::runtime_error {
public:
    explicit PyforaError(const std::string& s)
        : std::runtime_error(s)
        {
        }

    /*
      Polymorphic exception idiom
      https://en.wikibooks.org/wiki/More_C%2B%2B_Idioms/Polymorphic_Exception
     */
    virtual void raise() const
        {
        throw *this;
        }

    /*
      virtual ctor idiom. 
      https://en.wikibooks.org/wiki/More_C%2B%2B_Idioms/Virtual_Constructor

      should return a new'd object,
      which means it should probably be wrapped in a shared_ptr
      upon invocation
    */
    virtual PyforaError* clone() const
        {
        return new PyforaError(*this);
        }

    virtual void setPyErr() const {
        PyObjectPtr type = pyExcClass();

        PyErr_SetString(
            type.get(),
            what()
            );
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.Exceptions", "PyforaError");
        }

protected:
    static PyObjectPtr getModuleMember(const std::string& moduleName,
                                       const std::string& memberName)
        {
        PyObjectPtr exceptionsModule = PyObjectPtr::unincremented(
            PyImport_ImportModule(moduleName.c_str()));
        if (exceptionsModule == nullptr) {
            throw std::runtime_error(PyObjectUtils::exc_string());
            }

        PyObjectPtr tr = PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                exceptionsModule.get(),
                memberName.c_str()
                )
            );
        
        if (tr == nullptr) {
            throw std::runtime_error(PyObjectUtils::exc_string());
            }

        return tr;
        }
};


class PyforaInspectError : public PyforaError {
public:
    explicit PyforaInspectError(const std::string& s)
        : PyforaError(s)
        {
        }

    virtual PyforaInspectError* clone() const {
        return new PyforaInspectError(*this);
        }

    virtual void raise() const
        {
        throw *this;
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.PyforaInspect", "PyforaInspectError");
        }
};


class BadWithBlockError : public PyforaError {
public:
    explicit BadWithBlockError(const std::string& s)
        : PyforaError(s)
        {
        }

    virtual BadWithBlockError* clone() const {
        return new BadWithBlockError(*this);
        }

    virtual void raise() const
        {
        throw *this;
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.Exceptions", "BadWithBlockError");
        }
};


class CantGetSourceTextError : public PyforaError {
public:
    explicit CantGetSourceTextError(const std::string& s)
        : PyforaError(s)
        {
        }

    virtual CantGetSourceTextError* clone() const {
        return new CantGetSourceTextError(*this);
        }

    virtual void raise() const
        {
        throw *this;
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.Exceptions", "CantGetSourceTextError");
        }
};


class PythonToForaConversionError : public PyforaError {
public:
    explicit PythonToForaConversionError(const std::string& s)
        : PyforaError(s)
        {
        }

    virtual PythonToForaConversionError* clone() const {
        return new PythonToForaConversionError(*this);
        }

    virtual void raise() const
        {
        throw *this;
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.Exceptions", "PythonToForaConversionError");
        }
};


class UnresolvedFreeVariableExceptionWithTrace : public PyforaError {
public:
    explicit UnresolvedFreeVariableExceptionWithTrace(const PyObjectPtr& value)
        : PyforaError(""),
          mPtr(value)
        {
        }

    PyObjectPtr value() const {
        return mPtr;
        }

    virtual UnresolvedFreeVariableExceptionWithTrace* clone() const {
        return new UnresolvedFreeVariableExceptionWithTrace(*this);
        }

    virtual void raise() const
        {
        throw *this;
        }

    virtual PyObjectPtr pyExcClass() const {
        return getModuleMember("pyfora.UnresolvedFreeVariableExceptions",
                               "UnresolvedFreeVariableExceptionWithTrace");
        }

    virtual void setPyErr() const {
        PyObjectPtr type = pyExcClass();

        PyErr_SetObject(
            type.get(),
            mPtr.get()
            );
        }

private:
    PyObjectPtr mPtr;
};
