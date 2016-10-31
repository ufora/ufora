#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import ufora.native.FORA as ForaNative

RefcountStyle = getattr(ForaNative, "TypedFora::RefcountStyle")
CallTarget = getattr(ForaNative, "TypedFora::CallTarget")
TransferTarget = getattr(ForaNative, "TypedFora::TransferTarget")
Callable = getattr(ForaNative, "TypedFora::Callable")
Expression = getattr(ForaNative, "TypedFora::Expression")
ContinuationFrame = getattr(ForaNative, "TypedFora::ContinuationFrame")
Type = getattr(ForaNative, "TypedFora::Type")
Variable = getattr(ForaNative, "TypedFora::Variable")
InlineNativeOperationArg = getattr(ForaNative, "TypedFora::InlineNativeOperationArg")
ResultSignature = getattr(ForaNative, "TypedFora::ResultSignature")
BlockID = getattr(ForaNative, "TypedFora::BlockID")
Block = getattr(ForaNative, "TypedFora::Block")
Continuation = getattr(ForaNative, "TypedFora::Continuation")
MakeTupleArgument = getattr(ForaNative, "TypedFora::MakeTupleArgument")
MetadataInstruction = getattr(ForaNative, "TypedFora::MetadataInstruction")
MetadataVariable = getattr(ForaNative, "TypedFora::MetadataVariable")
MetadataStackFrame = getattr(ForaNative, "TypedFora::MetadataStackFrame")

VariableList = getattr(ForaNative, "ImmutableTreeVectorOfTypedFora::Variable")
MakeTupleArgumentList = getattr(ForaNative, "ImmutableTreeVectorOfTypedFora::MakeTupleArgument")
TypeList = getattr(ForaNative, "ImmutableTreeVectorOfTypedFora::Type")

