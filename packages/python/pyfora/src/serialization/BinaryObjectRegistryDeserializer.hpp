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

#include <memory>
#include <stdint.h>
#include <vector>


class ObjectRegistry;
class Deserializer;


class BinaryObjectRegistryDeserializer {
public:
    static void deserializeFromStream(
        std::shared_ptr<Deserializer> stream, 
        ObjectRegistry& binaryObjectRegistry,
        PyObject* convertJsonToObject // python callable
        );

private:
    static PyObject* readPrimitive(char code, std::shared_ptr<Deserializer> stream);
    static void readInt64s(std::shared_ptr<Deserializer> stream,
                           std::vector<int64_t>& ioInts);
    static PyObject* readSimplePrimitive(std::shared_ptr<Deserializer> stream);
    static PyObject* readFreeVariableResolutions(std::shared_ptr<Deserializer> stream);
    static PyObject* readStringTuple(std::shared_ptr<Deserializer> stream);
};
