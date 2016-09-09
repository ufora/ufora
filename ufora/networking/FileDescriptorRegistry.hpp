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
#pragma once

#include "../core/IntegerTypes.hpp"
#include <map>
#include <boost/thread/recursive_mutex.hpp>


class ScopedFileDescriptorRegisterer {
    class RegistrationInformation {
    public:
        RegistrationInformation(uint32_t inMaxRegistrationCount, uint32_t inCurrentRegistrationCount) :
            mMaxRegistrationCount(inMaxRegistrationCount),
            mCurrentRegistrationCount(inCurrentRegistrationCount) {}
        uint32_t                mMaxRegistrationCount;
        uint32_t                mCurrentRegistrationCount;
    };

    class FileDescriptorRegistry {
        public:
            bool acquireFd(uint32_t fd, uint32_t maxRegistrationCount);
            void releaseFd(uint32_t fd);
            static FileDescriptorRegistry& getRegistrySingleton(void);
            FileDescriptorRegistry();

        private:
            // noncopyable
            const FileDescriptorRegistry& operator=(const FileDescriptorRegistry&);
            FileDescriptorRegistry(const FileDescriptorRegistry&);

            boost::recursive_mutex                                   mMutex;
            std::map<uint32_t, RegistrationInformation>             mFdMap;

    };

    public:

        static void initialize(void);
        ScopedFileDescriptorRegisterer(uint32_t inFileDescriptor, uint32_t inMaxRegistrationCount);
        ~ScopedFileDescriptorRegisterer();
        bool sucessfullyRegistered(void);

    private:

        const ScopedFileDescriptorRegisterer& operator=(const ScopedFileDescriptorRegisterer&);
        ScopedFileDescriptorRegisterer(const ScopedFileDescriptorRegisterer&);

        uint32_t                                mFileDescriptor;
        bool                                    mAcquired;
};
