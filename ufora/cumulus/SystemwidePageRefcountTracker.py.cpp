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
#include <boost/python.hpp>
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/python/ScopedPyThreads.hpp"
#include "SystemwidePageRefcountTracker.hppml"

class SystemwidePageRefcountTrackerWrapper :
		public native::module::Exporter<SystemwidePageRefcountTrackerWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}
		
	void	getDefinedTypes(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(PolymorphicSharedPtr<SystemwidePageRefcountTracker>).name());
		}

	static boost::python::object machinesWithPageInRam(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker,
									Fora::PageId inPage
									)
		{
		std::set<Cumulus::MachineId> machineSet;

		tracker->machinesWithPageInRam(inPage, machineSet);

		return Ufora::python::containerWithBeginEndToList(machineSet);
		}

	static boost::python::object getAllPages(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker
									)
		{
		std::set<Fora::PageId> pages;

		tracker->getAllPages(pages);

		return Ufora::python::containerWithBeginEndToList(pages);
		}

	static boost::python::object getAllActivePages(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker
									)
		{
		std::set<Fora::PageId> pages;

		tracker->getAllPages(pages);

		std::set<Fora::PageId> active;

		for (auto page: pages)
			if (tracker->isPageAnywhereOnDisk(page) || tracker->isPageAnywhereInRam(page))
				active.insert(page);

		return Ufora::python::containerWithBeginEndToList(active);
		}

	static boost::python::object getPagesThatAppearOrphaned(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker
									)
		{
		return Ufora::python::containerWithBeginEndToList(tracker->pagesThatAppearOrphaned());
		}

	static boost::python::object getAllMachineIds(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker
									)
		{
		return Ufora::python::containerWithBeginEndToList(tracker->getAllMachineIds());
		}

	static boost::python::object machinesWithPageOnDisk(
									PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker,
									Fora::PageId inPage
									)
		{
		std::set<Cumulus::MachineId> machineSet;

		tracker->machinesWithPageOnDisk(inPage, machineSet);

		return Ufora::python::containerWithBeginEndToList(machineSet);
		}

	static bool pageIsInRam(PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker, 
							Fora::PageId inPageId, 
							Cumulus::MachineId inMachineId
							)
		{
		return tracker->pageIsInRam(inPageId, inMachineId);
		}

	static bool pageIsOnDisk(PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker, 
							Fora::PageId inPageId, 
							Cumulus::MachineId inMachineId
							)
		{
		return tracker->pageIsOnDisk(inPageId, inMachineId);
		}

	static std::string getViewOfSystem(
							PolymorphicSharedPtr<SystemwidePageRefcountTracker>& tracker
							)
		{
		return tracker->getViewOfSystem();
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<PolymorphicSharedPtr<SystemwidePageRefcountTracker> >(
											"SystemwidePageRefcountTracker", 
											no_init
											)
			.def("getAllPages", getAllPages)
			.def("getAllActivePages", getAllActivePages)
			.def("getAllMachineIds", getAllMachineIds)
			.def("pageIsInRam", pageIsInRam)
			.def("pageIsOnDisk", pageIsOnDisk)
			.def("machinesWithPageInRam", machinesWithPageInRam)
			.def("machinesWithPageOnDisk", machinesWithPageOnDisk)
			.def("getViewOfSystem", getViewOfSystem)
			.def("getPagesThatAppearOrphaned", getPagesThatAppearOrphaned)
			;
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<
	SystemwidePageRefcountTrackerWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			SystemwidePageRefcountTrackerWrapper>::registerWrapper();

