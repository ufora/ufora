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
#include "statsd.hpp"

#include "../native/Registrar.hpp"
#include <boost/python.hpp>

using namespace ufora;
using namespace boost::python;

BOOST_PYTHON_FUNCTION_OVERLOADS(Statsd_configure_overloads, Statsd::configure, 2, 3)
BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(Statsd_increment_overloads, Statsd::increment, 1, 2)
BOOST_PYTHON_MEMBER_FUNCTION_OVERLOADS(Statsd_decrement_overloads, Statsd::decrement, 1, 2)

class StatsdWrapper : public native::module::Exporter<StatsdWrapper>
{
public:
    std::string getModuleName(void)
        {
        return "Statsd";
        }

    static Statsd::Timer* createTimer(Statsd& statsd, const std::string& name)
        {
        Statsd::Timer* timer = new Statsd::Timer("");
        *timer = statsd.timer(name);
        return timer;
        }

    static void enterStatsdTimer(Statsd::Timer* timer)
        {
        // no-op
        }

    static void exitStatsdTimer(Statsd::Timer* timer, object o1, object o2, object o3)
        {
        timer->stop();
        }

    void exportPythonWrapper()
        {

        class_<Statsd>("Statsd")
            .def(init<>())
            .def(init<const std::string&>())
            .def("increment", &Statsd::increment,
                    Statsd_increment_overloads(
                        args("incrementBy")
                        )
                )
            .def("decrement", &Statsd::decrement,
                    Statsd_decrement_overloads(
                        args("decrementBy")
                        )
                )
            .def("gauge", &Statsd::gauge)
            .def("histogram", &Statsd::histogram)
            .def("timing", &Statsd::timing)
            .def("timer", createTimer, return_value_policy<manage_new_object>())
            ;

        class_<Statsd::Timer, boost::noncopyable>("StatsdTimer", no_init)
            .def("__enter__", enterStatsdTimer)
            .def("__exit__", exitStatsdTimer)
            ;

        def("configure", &Statsd::configure,
                    Statsd_configure_overloads(
                        args("prefix")
                        )
                    );
        }
};


//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<StatsdWrapper>::mEnforceRegistration =
            native::module::ExportRegistrar<StatsdWrapper>::registerWrapper();

