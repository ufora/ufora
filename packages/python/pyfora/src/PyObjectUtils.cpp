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
#include "PyObjectUtils.hpp"

#include <sstream>
#include <stdexcept>


std::string PyObjectUtils::repr_string(PyObject* obj)
    {
    PyObject* obj_repr = PyObject_Repr(obj);
    if (obj_repr == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't compute repr of an object");
        }
    if (not PyString_Check(obj_repr)) {
        throw std::runtime_error("repr returned a non string");
        }

    std::string tr = std::string(
        PyString_AS_STRING(obj_repr),
        PyString_GET_SIZE(obj_repr)
        );

    Py_DECREF(obj_repr);

    return tr;
    }


std::string PyObjectUtils::str_string(PyObject* obj)
    {
    PyObject* obj_str = PyObject_Str(obj);
    if (obj_str == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't compute repr of an object");
        }
    if (not PyString_Check(obj_str)) {
        throw std::runtime_error("repr returned a non string");
        }

    std::string tr = std::string(
        PyString_AS_STRING(obj_str),
        PyString_GET_SIZE(obj_str)
        );

    Py_DECREF(obj_str);

    return tr;
    }


std::string PyObjectUtils::std_string(PyObject* string)
    {
    if (PyString_Check(string))
        {
        return std::string(
            PyString_AS_STRING(string),
            PyString_GET_SIZE(string)
            );
        }
    else if (PyUnicode_Check(string)) {
        PyObject* s = PyUnicode_AsASCIIString(string);
        if (s == NULL) {
            throw std::runtime_error(
                "couldn't get an ascii string from a unicode string: " +
                PyObjectUtils::exc_string()
                );
            }

        std::string tr = std::string(
            PyString_AS_STRING(s),
            PyString_GET_SIZE(s)
            );
        
        Py_DECREF(s);

        return tr;
        }
    else {
        throw std::runtime_error("expected a string or unicode object");
        }
    }


std::string PyObjectUtils::format_exc()
    {
    PyObject * exception = NULL, * v = NULL, * tb = NULL;
    PyErr_Fetch(&exception, &v, &tb);
    if (exception == NULL) {
        return "<no exception>";
        }
    PyErr_NormalizeException(&exception, &v, &tb);

    PyObject* typeString = PyObject_Str(exception);
    Py_DECREF(exception);
    if (typeString == NULL) {
        Py_XDECREF(tb);
        Py_XDECREF(v);
        return "<INTERNAL ERROR: couldn't get typeString in PyObjectUtils::format_exc>";
        }
    if (not PyString_Check(typeString)) {
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        Py_XDECREF(v);
        return "<INTERNAL ERROR: str(exception) didn't return a string in" 
            " PyObjectUtils::format_exc";
        }

    if (v == NULL) {
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        return "<v unexpectedly none in PyObjectUtils::format_exc>";
        }
    PyObject* valueString = PyObject_Str(v);
    Py_DECREF(v);
    if (valueString == NULL) {
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        return "<INTERNAL ERROR: couldn't get value string>";
        }
    if (not PyString_Check(valueString)) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        return "<INTERNAL ERROR: str(v) didn't return a string!>";
        }

    PyObject* cStringIOModule = PyImport_ImportModule("cStringIO");
    if (cStringIOModule == NULL) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        throw std::runtime_error(
            "py error importing cStringIO module: " + 
            PyObjectUtils::exc_string()
            );
        }
    
    PyObject* StringIOClass = PyObject_GetAttrString(
        cStringIOModule,
        "StringIO");
    Py_DECREF(cStringIOModule);
    if (StringIOClass == NULL) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        throw std::runtime_error(
            "py error getting StringIO member on cStringIO in PyObjectUtils::format_exc: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* stringIO = PyObject_CallFunctionObjArgs(StringIOClass, NULL);
    Py_DECREF(StringIOClass);
    if (stringIO == NULL) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);
        Py_XDECREF(tb);
        throw std::runtime_error(
            "py error calling StringIO in PyObjectUtils::format_exc: " + 
            PyObjectUtils::exc_string()
            );
        }

    if (tb == NULL) {
        Py_DECREF(stringIO);
        Py_DECREF(valueString);
        Py_DECREF(typeString);        
        throw std::runtime_error(
            "<tb unexpectedly NULL in PyObjectUtils::format_exc>"
            );
        }
    int retcode = PyTraceBack_Print(tb, stringIO);
    Py_DECREF(tb);
    if (retcode < 0) {
        Py_DECREF(stringIO);
        Py_DECREF(valueString);
        Py_DECREF(typeString);        
        throw std::runtime_error(
            "error calling PyTraceBack_Print in PyObjectUtils::format_exc: " +
            PyObjectUtils::exc_string()
            );
        }
    PyObject* tb_string = PyObject_CallMethod(
        stringIO,
        const_cast<char*>("getvalue"),
        const_cast<char*>("()")
        );
    Py_DECREF(stringIO);
    if (tb_string == NULL) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);        
        throw std::runtime_error(
            "py error calling getvalue on a StringIO in PyObjectUtils::format_exc:" +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyString_Check(tb_string)) {
        Py_DECREF(tb_string);
        Py_DECREF(valueString);
        Py_DECREF(typeString);        
        throw std::runtime_error("<expected getvalue to return a string>");
        }

    std::ostringstream oss;

    oss.write(PyString_AS_STRING(typeString), PyString_GET_SIZE(typeString));
    oss << ": ";
    oss.write(PyString_AS_STRING(valueString), PyString_GET_SIZE(valueString));

    Py_DECREF(valueString);
    Py_DECREF(typeString);

    oss << "\n";
    
    oss.write(PyString_AS_STRING(tb_string), PyString_GET_SIZE(tb_string));

    Py_DECREF(tb_string);

    return oss.str();
    }


std::string PyObjectUtils::exc_string()
    {
    PyObject * exception = NULL, * v = NULL, * tb = NULL;

    /*
      From the Python C-API documentation: 

      PyErr_Fetch(PyObject** ptype, PyObject** value, PyObject** traceback)

      Retrieve the error indicator into three variables whose addresses are passed. 
      If the error indicator is not set, set all three variables to NULL.
      If it is set, it will be cleared and you own a reference to each object retrieved.
      The value and traceback object may be NULL even when the type object is not.
     */

    PyErr_Fetch(&exception, &v, &tb);
    if (exception == NULL) {
        return "<no exception>";
        }
    PyErr_NormalizeException(&exception, &v, &tb);
    Py_XDECREF(tb);

    PyObject* typeString = PyObject_Str(exception);
    Py_DECREF(exception);
    if (typeString == NULL) {
        Py_XDECREF(v);
        return "<INTERNAL ERROR: couldn't get typeString>";
        }
    if (not PyString_Check(typeString)) {
        Py_DECREF(typeString);
        Py_XDECREF(v);
        return "<INTERNAL ERROR: str(exception) didn't return a string!>";
        }

    PyObject* valueString = PyObject_Str(v);
    Py_XDECREF(v);
    if (valueString == NULL) {
        Py_DECREF(typeString);
        return "<INTERNAL ERROR: couldn't get value string>";
        }
    if (not PyString_Check(valueString)) {
        Py_DECREF(valueString);
        Py_DECREF(typeString);
        return "<INTERNAL ERROR: str(v) didn't return a string!>";
        }

    std::ostringstream oss;

    oss.write(PyString_AS_STRING(typeString), PyString_GET_SIZE(typeString));
    oss << ": ";
    oss.write(PyString_AS_STRING(valueString), PyString_GET_SIZE(valueString));

    Py_DECREF(valueString);
    Py_DECREF(typeString);

    return oss.str();
    }


long PyObjectUtils::builtin_id(PyObject* pyObject)
    {
    PyObject* pyObject_builtin_id = PyLong_FromVoidPtr(pyObject);
    if (pyObject_builtin_id == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get a builtin id");
        }

    int overflow;
    long tr = PyLong_AsLongAndOverflow(pyObject_builtin_id, &overflow);

    Py_DECREF(pyObject_builtin_id);

    if (overflow != 0) {
        throw std::runtime_error("overflow in converting a python long to a C long");
        }

    return tr;
    }


bool PyObjectUtils::in(PyObject* container, PyObject* value)
    {
    if (PySet_Check(container)) {
        return PySet_Contains(container, value);
        }
    else if (PyDict_Check(container)) {
        return PyDict_Contains(container, value);
        }
    else if (PyList_Check(container)) {
        return _in_list(container, value);
        }
    else {
        throw std::runtime_error("we haven't implemented all alternatives here. "
                               "should just call back into python."
            );
        }
    }


bool PyObjectUtils::_in_list(PyObject* pyList, PyObject* value)
    {
    int result;
    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(pyList); ++ix) {
        PyObject* item = PyList_GET_ITEM(pyList, ix);

        if (PyObject_Cmp(value, item, &result) == -1) {
            throw std::runtime_error("error calling cmp");
            }

        if (result == 0) {
            return true;
            }
        }

    return false;
    }
