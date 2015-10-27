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
#ifndef SharedState_PY_HPP
#define SharedState_PY_HPP

#include <stdint.h>
#include <boost/python.hpp>
#include <sstream>
#include "View.hppml"
#include "Common.hpp"
#include "Types.hppml"
#include "KeyspaceManager.hppml"
#include "Storage/FileStorage.hppml"
#include "KeyRangeSet.hppml"
#include "Storage/LogEntry.hppml"
#include "../../networking/Channel.hpp"
#include "../../networking/SocketStringChannel.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/python/utilities.hpp"
#include "../../core/serialization/Serialization.hpp"
#include "../../core/serialization/CPPMLSerializer.hppml"

using namespace Ufora::python;
using namespace SharedState;

template<class T>
bool op_equal(const T& lhs, const T& rhs)
	{
	return lhs == rhs;
	}

template<class T>
bool op_lt(const T& lhs, const T& rhs)
	{
	return lhs < rhs;
	}
template<class T>
bool op_gt(const T& lhs, const T& rhs)
	{
	return !(lhs < rhs || lhs == rhs);
	}

template<class T>
Nullable<T> make_nullable(boost::python::object value)
	{
	return (value == boost::python::object()) ? null() : Nullable<T>(boost::python::extract<T>(value));
	}


inline boost::python::object kr_right(KeyRange& kr)
	{
	if (!kr.right())
		return boost::python::object();
	else
		return boost::python::make_tuple((*kr.right()).value(), (*kr.right()).leftBound());
	}

inline boost::python::object kr_left(KeyRange& kr)
	{
	if (!kr.left())
		return boost::python::object();
	else
		return boost::python::make_tuple((*kr.left()).value(), (*kr.left()).leftBound());
	}

inline Keyspace kr_keyspace(KeyRange& kr)
	{
	return kr.keyspace();
	}



inline bool py_bound_lt(boost::python::object left, bool leftIsLeft, boost::python::object right, bool rightIsLeft) // for testing
	{
	return boundLT(make_nullable<KeyBound>(left), leftIsLeft, make_nullable<KeyBound>(right), rightIsLeft);
	}

inline bool py_bound_eq(boost::python::object left, bool leftIsLeft, boost::python::object right, bool rightIsLeft) // for testing
	{
	return boundEQ(make_nullable<KeyBound>(left), leftIsLeft, make_nullable<KeyBound>(right), rightIsLeft);
	}

inline void krs_insert(KeyRangeSet& inSet, const KeyRange& inRange)
	{
	set<KeyRange> temp = inSet.difference(inRange);
	inSet.insert(temp);
	}

inline boost::python::object krs_get_ranges(KeyRangeSet& krs)
	{
	return containerWithBeginEndToList(krs);
	}

inline boost::python::object krs_intersection(KeyRangeSet& krs, KeyRange& range)
	{
	return containerWithBeginEndToList(krs.intersection(range));
	}

inline Ufora::Json keyspace_name(const Keyspace& keyspace)
	{
	return keyspace.name();
	}

inline string keyspace_type(const Keyspace& keyspace)
	{
	return keyspace.type();
	}

inline uint32_t keyspace_dimension(const Keyspace& keyspace)
	{
	return keyspace.dimension();
	}




using namespace SharedState;

template<class T>
class PythonWrapper;

template<>
class PythonWrapper<View>	{
public:

		static void osErrorTranslator(Ufora::OsError arg)
			{
			PyErr_SetFromErrno(PyExc_OSError);
			}

		static void sTest(uint32_t loops, MessageOut message)
			{
			for(uint32_t i = 0; i < loops; i++)
				deepcopy(deepcopy(message));
			}

		static Keyspace partialEventKeyspace(const PartialEvent& event)
			{
			return event.keyspace();
			}
		static Key partialEventKey(const PartialEvent& event)
			{
			return event.key();
			}



		static MessageOut createMessage(string inMessage)
			{
			vector<KeyNameType> id;

			id.push_back(Ufora::Json::String("asdf"));
			id.push_back(Ufora::Json::String("channelId"));
			vector<KeyUpdate> updates;
			updates.push_back(
				KeyUpdate(
					Key(client_info_keyspace, id), 
					null() << Ufora::Json::String(inMessage)
					)
				);
			Event event(UniqueId(0, 0), updates);
			map<Key, PartialEvent> out;
			event.split(out);
			return MessageOut::PushEvent(out.begin()->second);
			}
		static Keyspace get_client_info_keyspace(void)
			{
			return client_info_keyspace;
			}
		
		static uint32_t view_id(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			return v->getClientId();
			}
		static boost::python::object view_get_client_id(PolymorphicSharedPtr<View>& v)
			{
			Nullable<uint32_t> tr;
			tr = v->getClientIdNowait();
			if (!tr)
				return boost::python::object();
			return boost::python::object(*tr);	
			}
		static boost::python::object prevKey(PolymorphicSharedPtr<View>& v, const Key& key)
			{
			Nullable<Key> tr;
				{
				ScopedPyThreads scoper;
				tr = v->prevKey(key);
				}

			if (tr)
				return boost::python::object(*tr);
			return boost::python::object();
			}
		static boost::python::object nextKey(PolymorphicSharedPtr<View>& v, const Key& key)
			{
			Nullable<Key> tr;
			
				{
				ScopedPyThreads scoper;
				tr = v->nextKey(key);
				}

			if (tr)
				return boost::python::object(*tr);
			return boost::python::object();
			}
		static boost::python::object getValue(PolymorphicSharedPtr<View>& v, const Key& key)
			{
			Nullable<ValueType> tr;
			
				{
				ScopedPyThreads scoper;
				tr = v->getValue(key);
				}

			if (tr)
				return boost::python::object(*tr);
			return boost::python::object();
			}
		static boost::python::object value_getVal(const ValueType& v)
			{
			Nullable<ValueData> tr = v.value();
			if (tr)
				return boost::python::object(*tr);
			return boost::python::object();
			}
		static uint64_t value_getId(const ValueType& v)
			{
            return v.id().eventId();
            }
		
        static Nullable<Ufora::Json> pyToJson(boost::python::object o)
        	{
			boost::python::extract<Ufora::Json> extractJson(o);
			
			if (extractJson.check())
				return null() << extractJson();

			return null();
        	} 
		
        static Ufora::Json pyToJsonOrError(boost::python::object o)
        	{
			boost::python::extract<Ufora::Json> extractJson(o);
			
			if (extractJson.check())
				return extractJson();

			lassert_dump(false, "couldn't convert argument to json");
        	}

		static void updateKey(PolymorphicSharedPtr<View>& v, const Key& key, boost::python::object o)
			{
			if (o == boost::python::object())
				{
				ScopedPyThreads scoper;
				v->write(KeyUpdate(key, UpdateType()));
				return;
				}
			
			Nullable<Ufora::Json> json = pyToJson(o);

			if (json)
				{
				ScopedPyThreads scoper;
				v->write(KeyUpdate(key, UpdateType(json)));
				return;
				}
			
			lassert_dump(false, "bad key value " << Ufora::python::pyToString(o) 
					<< ": should be string, Json, or None");
			}

		static boost::python::object makeInMemoryChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)
			{
			auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(inCallbackScheduler);

			return boost::python::make_tuple(
				makeQueuelikeChannel(
					inCallbackScheduler,
					new serialized_channel_type(inCallbackScheduler, pRaw.first)
					),
				makeQueuelikeChannel(
					inCallbackScheduler, 
					new serialized_manager_channel_type(inCallbackScheduler, pRaw.second)
					)
				);
			}


		static boost::python::object makeInMemoryChannelWithoutMemo(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)
			{

			typedef SerializedChannel<
						MessageOut,  
						MessageIn, 
						BinaryStreamSerializer, 
						BinaryStreamDeserializer
						>						 						view_channel_type;

			typedef SerializedChannel<
						MessageIn, 
						MessageOut,  
						BinaryStreamSerializer, 
						BinaryStreamDeserializer
						>						 						manager_channel_type;


			auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(inCallbackScheduler);

			return boost::python::make_tuple(
				makeQueuelikeChannel(
					inCallbackScheduler,
					new view_channel_type(inCallbackScheduler, pRaw.first)
					),
				makeQueuelikeChannel(
					inCallbackScheduler,
					new manager_channel_type(inCallbackScheduler, pRaw.second)
					)
				);
			}


		static boost::python::object makeViewToSerializedChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)

			{
			auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(inCallbackScheduler);

			return boost::python::make_tuple(
				makeQueuelikeChannel(
					inCallbackScheduler,
					new serialized_channel_type(inCallbackScheduler, pRaw.first)
					),
				makeQueuelikeChannel(
					inCallbackScheduler,
					pRaw.second
					)
				);
			}

		static boost::python::object makeSerializedToManagerChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
				)
			{
			auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(inCallbackScheduler);

			return boost::python::make_tuple(
				makeQueuelikeChannel(
					inCallbackScheduler,
					pRaw.second 
					),

				makeQueuelikeChannel(
					inCallbackScheduler,
					new serialized_manager_channel_type(inCallbackScheduler, pRaw.first)
					)
				);
			}

		static boost::python::object makeClientSocketMessageChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				int32_t inFileDescriptor
				)
			{
			return boost::python::object(
				makeQueuelikeChannel(
					inCallbackScheduler,
					new serialized_channel_type(
						inCallbackScheduler,
						PolymorphicSharedPtr<Channel<std::string, std::string> >(
							new SocketStringChannel(inCallbackScheduler, inFileDescriptor)
							)
						)
					)
				);
			}

		static boost::python::object makeServerSocketChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				int32_t inFileDescriptor
				)
										
			{
			return boost::python::object(
				makeQueuelikeChannel(
					inCallbackScheduler,
					new serialized_manager_channel_type(
						inCallbackScheduler,
						PolymorphicSharedPtr<Channel<std::string, std::string> >(
							new SocketStringChannel(inCallbackScheduler, inFileDescriptor)
							)

						)
					)
				);
			}

		static string_channel_ptr_type makeSerializedSocketChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				int32_t inFileDescriptor
				)
			{
			return makeQueuelikeChannel(
				inCallbackScheduler,
				new SocketStringChannel(inCallbackScheduler, inFileDescriptor)
				);
			}

		static KeyRange makeKeyRange(
							const Keyspace& keyspace, 
							uint32_t index, 
							boost::python::object leftBound, 
							boost::python::object rightBound, 
							bool leftInclusive, 
							bool rightInclusive)
			{
			using namespace boost::python;

			Nullable<KeyBound> left;
			Nullable<KeyBound> right;

			if (leftBound.ptr() == object().ptr())
				left = null();
			else
				left = Nullable<KeyBound>(KeyBound(pyToJsonOrError(leftBound), leftInclusive));

			if (rightBound.ptr() == object().ptr())
				right = null();
			else
				right = Nullable<KeyBound>(KeyBound(pyToJsonOrError(rightBound), !rightInclusive));

			return KeyRange(keyspace, index, left, right);
			}


		static void subscribe(PolymorphicSharedPtr<View>& v, const KeyRange& range)
			{
			ScopedPyThreads scoper;

			v->subscribe(range, true);
			}
		static void subscribe2(PolymorphicSharedPtr<View>& v, const KeyRange& range, bool waitLoad = true)
			{
			ScopedPyThreads scoper;

			v->subscribe(range, waitLoad);
			}
		static void unsubscribe2(PolymorphicSharedPtr<View>& v, const KeyRange& range)
			{
			ScopedPyThreads scoper;

			v->unsubscribe(range);
			}

		static void disconnect(PolymorphicSharedPtr<View>& v)
			{
			v->disconnect();
			}

		static void wait_range(PolymorphicSharedPtr<View>& v, const KeyRange& range)
			{
			ScopedPyThreads scoper;

			set<KeyRange> s;
			s.insert(range);
			v->waitForSubscription(s);
			}
		static void wait_range_cgss(PolymorphicSharedPtr<View>& v, boost::python::object keyspace)
			{
			ScopedPyThreads scoper;

			set<KeyRange> s;
			s.insert(KeyRange(Keyspace("TakeHighestIdKeyType", pyToJsonOrError(keyspace), 1), 0, null(), null()));
			v->waitForSubscription(s);
			}

		static string value_str(const ValueType& v)
			{
			ostringstream tr;
			tr << v;
			return tr.str();
			}
		static void unsubscribe(PolymorphicSharedPtr<View>& v, uint32_t index, Keyspace& keyspace)
			{
			ScopedPyThreads scoper;
			v->unsubscribe(KeyRange(keyspace, index, null(), null()));
			}

		static Key* CreateKey(Keyspace& inKeyspace, boost::python::tuple inTup)
			{
			using namespace boost::python;
			vector<KeyNameType> tr;

			for(uint32_t i = 0; i < extract<uint32_t>(inTup.attr("__len__")()); i++)
				tr.push_back(pyToJsonOrError(inTup[i]));
			
			lassert_dump(inKeyspace.dimension() == tr.size(),
				"can't create a keyspace of dimension "
					<< inKeyspace.dimension() << " with a tuple of dimension "
					<< tr.size()
					);

			return new Key(inKeyspace, tr);
			}



		static Ufora::Json key_keyspace(const Key& inKey)
			{
			return inKey.keyspace().name();
			}
		static Ufora::Json key_keyname(const Key& inKey)
			{
			return inKey.id()[0];
			}
		static Ufora::Json key_operator_index(const Key& inKey, const uint32_t ix)
			{
			lassert_dump(ix < inKey.id().size(), "out of bounds: " << ix << " not < " << inKey.id().size())
			return inKey.id()[ix];
			}

		// the following two methods are for testing in python only....
		static int32_t key_cmp(const Key& inKey, boost::python::object& other)
			{
			boost::python::extract<Key> extract(other);
			if (!extract.check())
				return -1;

			const Key& otherKey(extract());

			if (inKey < otherKey)
				return -1;
				else
			if(inKey == otherKey)
				return 0;
			
			return 1;
			}

		static int32_t key_hash(const Key& inKey)
			{
			// not a good hash function but should work for testing purposes
			uint32_t val = 0;
			string contents = key_to_str(inKey);
			for (size_t i = 0; i < contents.size(); i+=4)
				{
				size_t maxIx = min(i + 3, contents.size() - 1);
				int8_t chars[] = {contents[i], contents[min(i + 1, maxIx)], contents[min(i + 2, maxIx)], contents[min(i + 3, maxIx)]};
				val += *((int*)chars);
				}
			return val;
			}

		static string key_to_str(const Key& inKey)
			{
			std::ostringstream s;

			s << "Key(" << prettyPrintString(inKey.keyspace().name()) << ", (";
			
			for (long k = 0; k < inKey.id().size();k++)
				s << prettyPrintString(inKey.id()[k]) << (k + 1 < inKey.id().size() ? ", " : "");
			
			s << "))";

			return s.str();
			}

		template<class T>
		static string to_str(T& v)
			{
			ostringstream tr;
			tr << v;
			return tr.str();
			}


		static void view_flush(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			v->flush(false);
			}
		static void view_flush_specify_assert(PolymorphicSharedPtr<View>& v, bool assertNotFrozen)
			{
			ScopedPyThreads scoper;
			v->flush(assertNotFrozen);
			}
		static void view_begin(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			v->begin();
			}

		static void view_end(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			v->end();
			}

		static uint32_t view_abort(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			return v->abort();
			}

		static bool view_frozen(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			return v->isFrozen();
			}

		static bool view_connected(PolymorphicSharedPtr<View>& v)
			{
			ScopedPyThreads scoper;
			return v->connected() > 0;
			}

		static void waitConnect(PolymorphicSharedPtr<View>& inView)
			{
			ScopedPyThreads releasePythonGIL;

			inView->waitConnect();
			}

		static bool waitConnectTimeout(PolymorphicSharedPtr<View>& inView, double inTimeout)
			{
			ScopedPyThreads releasePythonGIL;

			return inView->waitConnectTimeout(inTimeout);
			}

		static PolymorphicSharedPtr<View> createView(bool inDebugTracing)
			{
			return PolymorphicSharedPtr<View>(PolymorphicSharedPtr<View>(new View(inDebugTracing)));
			}
		static std::string view_to_str(PolymorphicSharedPtr<View>& v)
			{
			return to_str(*v.get());
			}

		static void view_set_must_subscribe(PolymorphicSharedPtr<View>& v, bool inMustSubscribe)
			{
			v->setMustSubscribe(inMustSubscribe);
			}
		static void view_add(PolymorphicSharedPtr<View>& v, channel_ptr_type& inChannel)
			{
			v->add(inChannel);
			}
		static void view_teardown(PolymorphicSharedPtr<View>& v)
			{
			v->teardown();
			}
		
		static KeyspaceManager::pointer_type* createKeyspaceManager(
				uint32_t inSeedVal, 
				uint32_t numManagers, 
				uint32_t backupInterval, 
				double pingInterval, 
				boost::python::object storageOrNone
				)
			{
			PolymorphicSharedPtr<FileStorage> inStorage;

			if (storageOrNone != boost::python::object())
				inStorage = boost::python::extract<PolymorphicSharedPtr<FileStorage> >(storageOrNone)();

			return new KeyspaceManager::pointer_type(
				new KeyspaceManager(
					inSeedVal, 
					numManagers, 
					backupInterval, 
					pingInterval, 
					inStorage
					)
				);
			}

		template<class T>
		static int cppmlCmpPy(const T& l, const T& r)
			{
			return cppmlCmp(l,r);
			}

		template<class T>
		static int cppmlHashPy(const T& l)
			{
			return hashCPPMLDirect(l)[0];
			}

		static KeyspaceManager::pointer_type* createKeyspaceManager2(
				uint32_t inSeedVal, 
				uint32_t numManagers, 
				uint32_t backupInterval, 
				double pingInterval
				)
			{
			return new KeyspaceManager::pointer_type(
				new KeyspaceManager(
					inSeedVal, 
					numManagers, 
					backupInterval, 
					pingInterval, 
					PolymorphicSharedPtr<FileStorage>()
					)
				);
			}



		static void keyspace_manager_add(	KeyspaceManager::pointer_type& inHolder, 
										manager_channel_ptr_type& inChannel
										)
			{
			inHolder->add(inChannel);
			}

		static void keyspace_manager_add_event(	KeyspaceManager::pointer_type& inHolder, 
										const PartialEvent& event
										)
			{
			inHolder->addEvent(event);
			}


		static void keyspace_manager_check(KeyspaceManager::pointer_type& inHolder)
			{
			inHolder->check();
			}

		static boost::python::object keyspace_manager_get_all_keyspaces(KeyspaceManager::pointer_type& inHolder)
			{
			vector<Keyspace> tr = inHolder->getAllKeyspaces();
			return iteratorPairToList(tr.begin(), tr.end());
			}

		static void keyspace_manager_shutdown(KeyspaceManager::pointer_type& inHolder)
			{
			inHolder->shutdown();
			}

		static PolymorphicSharedPtr<FileStorage> keyspace_manager_storage(KeyspaceManager::pointer_type& inHolder)
			{
			return inHolder->storage();
			}

		template<typename channel_type, typename out_message_type>
		static out_message_type channel_get(channel_type& channel)
			{
			ScopedPyThreads releasePythonGIL;
			
			return channel->get();
			}

		template<typename channel_type, typename in_message_type>
		static void channel_write(channel_type& channel, in_message_type& in)
			{
			ScopedPyThreads releasePythonGIL;

			channel->write(in);
			}

		template<typename channel_type>
		static void channel_disconnect(channel_type& channel)
			{
			channel->disconnect();
			}

        // this is necessary because the boost::python conversion doesn't 
        // seem to work correctly with a string&
		static void serialized_channel_write(string_channel_ptr_type& channel, string in)
			{
			ScopedPyThreads releasePythonGIL;

			channel->write(in);
			}

		static boost::python::object messageOutGetBundleElements(MessageOut& msg)
			{
			if (!msg.isBundle())
				return boost::python::object();
			
			boost::python::list l;

			for (long k = 0; k < msg.getBundle().messages().size(); k++)
				l.append(msg.getBundle().messages()[k]);

			return l;
			}

		static boost::python::object messageInGetBundleElements(MessageIn& msg)
			{
			if (!msg.isBundle())
				return boost::python::object();
			
			boost::python::list l;

			for (long k = 0; k < msg.getBundle().messages().size(); k++)
				l.append(msg.getBundle().messages()[k]);

			return l;
			}

		static boost::python::object messageOutMakeBundle(boost::python::list elements)
			{
			vector<MessageOut> elts;
			Ufora::python::toCPP(elements, elts);
			return boost::python::object(
				MessageOut::Bundle(elts)
				);
			}

		static boost::python::object messageOutRequestSession()
			{
			return boost::python::object(
					MessageOut::RequestSession(null())
					);
			}


		static boost::python::object messageInMakeBundle(boost::python::list elements)
			{
			vector<MessageIn> elts;
			Ufora::python::toCPP(elements, elts);
			return boost::python::object(
				MessageIn::Bundle(elts)
				);
			}



		static Keyspace* CreateKeyspace(std::string type, boost::python::object name, int32_t dim)
			{
			return new Keyspace(type, pyToJsonOrError(name), dim);
			}
		
		static KeyBound* CreateKeyBound(boost::python::object bound, bool isLeft)
			{
			return new KeyBound(pyToJsonOrError(bound), isLeft);
			}

		static void exportPythonInterface()
			{
			using namespace boost::python;
 
			boost::python::register_exception_translator<Ufora::OsError>(&osErrorTranslator);

			class_<channel_ptr_type>("ViewChannel", no_init)
				.def("get", &channel_get<channel_ptr_type, MessageIn>)
				.def("write", &channel_write<channel_ptr_type, MessageOut>)
				.def("disconnect", &channel_disconnect<channel_ptr_type>)
				;

			class_<manager_channel_ptr_type>("ManagerChannel", no_init)
				.def("get", &channel_get<manager_channel_ptr_type, MessageOut>)
				.def("write", &channel_write<manager_channel_ptr_type, MessageIn>)
				.def("disconnect", &channel_disconnect<manager_channel_ptr_type>)
				;
				
			class_<KeyspaceManager::pointer_type >("KeyspaceManager", no_init)
				.def("__init__", make_constructor(&createKeyspaceManager))
				.def("__init__", make_constructor(&createKeyspaceManager2))
				.def("add", &keyspace_manager_add)
				.def("addEvent", &keyspace_manager_add_event)
				.def("check", &keyspace_manager_check)
				.def("shutdown", &keyspace_manager_shutdown)
				.def("getAllKeyspaces", &keyspace_manager_get_all_keyspaces)
				.add_property("storage", &keyspace_manager_storage)
				;


			Ufora::python::CPPMLWrapper<LogEntry>(true).class_()
				.def("__cmp__", cppmlCmpPy<LogEntry>)
				;

			class_<KeyRange>("KeyRange")
				.def("__str__", &to_str<KeyRange>)
				.add_property("keyspace", &kr_keyspace)
				.def("left", &kr_left)
				.def("right", &kr_right)
				.def("__eq__", &op_equal<KeyRange>)
				.def("__lt__", &op_lt<KeyRange>)
				.def("__gt__", &op_gt<KeyRange>)
				;

			class_<KeyRangeSet>("KeyRangeSet")
				.def("insert", &krs_insert)
				.def("getRanges", &krs_get_ranges)
				.def("intersection", &krs_intersection)
				.def("erase", &KeyRangeSet::erase)
				.def("printRanges", &KeyRangeSet::printRanges)
				.def("printFuncs", &KeyRangeSet::printFuncs)
				;

			class_<Keyspace>("Keyspace", no_init)
				.def("__init__", make_constructor(CreateKeyspace))
				.add_property("name", &keyspace_name)
				.add_property("type", &keyspace_type)
				.add_property("dimension", &keyspace_dimension)
				.def("__cmp__", &cppmlCmpPy<Keyspace>)
				.def("__cmp__", &cppmlHashPy<Keyspace>)
				;

			class_<Key>("Key", no_init)
				.def("__init__", make_constructor(CreateKey))
				.def("__getitem__", &key_operator_index)
				.def("__cmp__", &key_cmp)
				.def("__hash__", &key_hash)
				.def("__len__", &Key::dimension)
				.def("__str__", &key_to_str)
				.def("__repr__", &key_to_str)
				.add_property("keyspace", &key_keyspace)
				.add_property("firstKeyDimension", &key_keyname)
				;

			class_<ValueType>("ValueType", no_init)
				.def("__str__", &to_str<ValueType>)
				.def("value", &value_getVal)
				.def("id", &value_getId)
				;

			def("MessageRequestSession", &messageOutRequestSession);

			Ufora::python::CPPMLWrapper<PartialEvent>(true).class_()
				.def("keyspace", &partialEventKeyspace)
				.def("key", &partialEventKey)
				;

			Ufora::python::CPPMLWrapper<MessageOut>(true).class_()
				.def("getBundleElements", messageOutGetBundleElements)
				.def("MakeBundle", messageOutMakeBundle)
				.staticmethod("MakeBundle")
				;
			Ufora::python::CPPMLWrapper<MessageIn>(true).class_()
				.def("getBundleElements", messageInGetBundleElements)
				.def("MakeBundle", messageInMakeBundle)
				.staticmethod("MakeBundle")
				;

			
			class_<KeyBound>("KeyBound", no_init)
				.def("__init__", make_constructor(CreateKeyBound));

			class_<PolymorphicSharedPtr<View> >("View", no_init)
				.def("__getitem__", &getValue)
				.def("__setitem__", &updateKey)
				.def("__str__", &view_to_str)
				.def("__repr__", &view_to_str)
				.def("rand", &View::rand)
				.def("setMustSubscribe", &view_set_must_subscribe)
				.def("randInt", &View::randInt)
				.def("flush", &view_flush)
				.def("flush", &view_flush_specify_assert)
				.def("add", &view_add)
				.def("begin", &view_begin)
				.def("end", &view_end)
				.def("abort", &view_abort)
				.def("prevKey", &prevKey)
				.def("nextKey", &nextKey)
				.def("waitForRange", &wait_range_cgss)
				.def("waitForRange", &wait_range)
				.def("disconnect", &disconnect)
				.def("subscribe", &subscribe)
				.def("subscribe", &subscribe2)
				.def("unsubscribe", &unsubscribe2)
				.def("unsubscribe", &unsubscribe)
				.def("getClientId", &view_get_client_id)
				.def("waitConnect", &waitConnect) 
				.def("waitConnectTimeout", &waitConnectTimeout) 
				.def("teardown", &view_teardown) 
				.add_property("id", &view_id)
				.add_property("isFrozen", &view_frozen)
				.add_property("connected", &view_connected)
				;

			def("createView", &createView);
			def("InMemoryChannel", makeInMemoryChannel);
			def("InMemoryChannelWithoutMemo", makeInMemoryChannelWithoutMemo);


			def("ViewToSerializedChannel", makeViewToSerializedChannel);
			def("SerializedToManagerChannel", makeSerializedToManagerChannel);

			def("serializeTest", sTest);
			def("boundLT", py_bound_lt);
			def("boundEQ", py_bound_eq);
			def("createMessage", createMessage);
			def("makeKeyRange", makeKeyRange);

			def("ClientSocketMessageChannel", makeClientSocketMessageChannel);
			def("ServerSocketChannel", makeServerSocketChannel);
			def("SerializedSocketChannel", makeSerializedSocketChannel);
			def("getClientInfoKeyspace", &get_client_info_keyspace);
			}
};











#endif

