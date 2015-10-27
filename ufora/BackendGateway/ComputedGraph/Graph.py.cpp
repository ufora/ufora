/***************************************************************************
   Copyright 2015 Ufora Inc.

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
#include <stdint.h>
#include <boost/python.hpp>
#include "Graph.hpp"
#include "Root.hpp"
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"

using namespace boost::python;
using namespace ComputedGraph;
    
class ComputedGraphWrapper :
    public native::module::Exporter<ComputedGraphWrapper> {
public:
    std::string     getModuleName(void)
        {
        return "ComputedGraph";
        }

    typedef PolymorphicSharedPtr<ComputedGraph::Graph> graph_ptr;

    static bool __eq__(graph_ptr& inGraph, graph_ptr& other)
        {
        return inGraph.get() == other.get();
        }

    static void __enter__(graph_ptr& inGraph)
        {
        Ufora::python::Holder h("pushCurGraph", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
        h.get()(inGraph->polymorphicSharedPtrFromThis());
        }

    static void __exit__(graph_ptr& inGraph, object o1, object o2, object o3)
        {
        Ufora::python::Holder h("popCurGraph", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
        h.get()();
        }

    static uword_t  __hash__(graph_ptr& inGraph)
        {
        return (uword_t)(void*)inGraph.get();
        }

    static std::string __str__(graph_ptr& inGraph)
        {
        std::stringstream ss;
        ss << "<ufora.native.ComputedGraph object at " << (void*)__hash__(inGraph) << ">";
        return ss.str();
        }

    static boost::python::object getNode_(graph_ptr& inGraph, boost::python::object inNodeType, boost::python::dict inInstanceData)
        {
        return inGraph->getNode_(inNodeType, inInstanceData);
        }

    static void flush(graph_ptr& inGraph)
        {
        inGraph->flushAll();
        }

    static void flushLazy(graph_ptr& inGraph, double timeout)
        {
        inGraph->flushLazy(timeout);
        }

    static void flushOrphans(graph_ptr& inGraph)
        {
        inGraph->flushOrphans();
        }

    static graph_ptr* constructCG(void)
        {
        return new graph_ptr(new ComputedGraph::Graph());
        }
    
    void exportPythonWrapper()
        {
        using namespace boost::python;

        class_<graph_ptr>("ComputedGraph", no_init)
                .def("__init__", make_constructor(constructCG))
                .def("__enter__", __enter__)
                .def("__eq__", __eq__)
                .def("__exit__", __exit__)
                .def("__hash__", __hash__)
                .def("__str__", __str__)
                .def("flush", flush)
                .def("flushLazy", flushLazy)
                .def("flushOrphans", flushOrphans)
                .def("getNode_", &getNode_)
                ;
        }
};






//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputedGraphWrapper>::mEnforceRegistration =
    native::module::ExportRegistrar<ComputedGraphWrapper>::registerWrapper();




