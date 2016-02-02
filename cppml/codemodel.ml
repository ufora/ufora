open Str;;
open Util;;
(* control how to see code output: *)

module String_set = Set.Make(String);;

let seen = ref String_set.empty;;

let args = Array.to_list(Sys.argv);;
let fullExpansion = List.exists (function x->x="-f") args;;
let guardedPreamble = List.exists (function x->x="--guarded-preamble") args;;
let noPreamble = List.exists (function x->x="--no-preamble") args;;

(* control how we increment and decrement refcounts. can be overridden. *)
let useAtomicOps = List.exists (function x->x="-atomic_ops") args;;

let add_in_type_to x = List.map (function name -> "in_" ^ name ^ "_type") x ;;
let add_type_to x = List.map (function name -> name ^ "_type") x ;;
let add_class_to x = List.map (function name -> "class " ^ name) x ;;
let comma_sep x = String.concat ", " x ;;
let template_def x = "template < " ^ (comma_sep (add_class_to x)) ^ " > ";;
let template_def_if_necessary x = (if List.length x > 0 then template_def x else "");;
let template_args x = " < " ^ (comma_sep (x)) ^ " > ";;
let template_args_if_necessary x = (if List.length x > 0 then template_args x else "");;


(* helper functions *)

let first (x,y) = x;;
let second (x,y) = y;;
let list_pair_cons ((a1,b1),(a2,b2)) = (a1::a2, b1::b2);;


let sep separ strfun lst = List.fold_left( function so_far -> function v -> so_far ^ (if (so_far = "") then "" else separ) ^ strfun(v) ) ("") (lst);;
let sep_with_indices separ strfun lst = first(List.fold_left( function (so_far,ix) -> function v -> (so_far ^ (if (so_far = "") then "" else separ) ^ strfun(v,ix), ix + 1) ) ("",0) (lst));;

let map_with_indices f lst = List.rev(first(List.fold_right( function v -> function (so_far,ix) -> (f(v,ix) :: so_far, ix + 1) ) (List.rev lst) ([],0) ));;


let newline = if fullExpansion = true then "\n" else "";;
let process_whitespace = if fullExpansion = true then (function w -> w) else (function w->w);;

(*tabify a string *)
let rec tabify s =
    String.concat "" ("\t" :: (List.map (function t -> if t = '\n' then "\n\t" else (String.make 1 t)) (str_to_list s) ) )
and
    str_to_list s =
        str_to_list_num s 0
and
    str_to_list_num s n = if n < String.length(s) then (s.[n] :: str_to_list_num s (n + 1)) else []
    ;;

let cppmlMatchVariableIncrementer = ref 0;;

let cppmlMatchVariableName baseName = (
	let curRefCt = !cppmlMatchVariableIncrementer in(
	cppmlMatchVariableIncrementer := curRefCt + 1;
	
	baseName ^ "_" ^ string_of_int(curRefCt)
	));;

(* type definitions *)

type named_type_op = NoTypeOp | TypeOp of string;;


	(* representation of what's coming out of the parser

	this is a very simple parse of the C++ - it mostly contains simple
	grouping and scoping information so that we can correctly generate
	@type information within namespaces and classes

	*)
type
    whitespace = string
and code =
        Token of string
	|	Whitespace of string
    |   Sequence of code list
    |   Grouping of scoping * code
    |   Type of (template_term list) * ml_type list
    |   MatchExpression of string * code * match_term list
and scoping =
		ClassOrNamespaceScope of string
	|	TemplateScope of template_term list
and template_term = string * string * template_default_value
and template_default_value = NoTemplateDefault | TemplateDefault of string
and optional_member_name =
        Named of string
    |   Unnamed
and unnamed_type =
        CPPTypes of (string * optional_member_name * whitespace) list * (string * optional_member_name * whitespace * code) list  (* second is memo-ed definitions *)
and
	optional_memo =
		NoMemo
	|	Memo of whitespace * code
and named_type =
        NamedType of string * whitespace * unnamed_type * named_type_op * whitespace
and ml_type_body =
        Alternatives of named_type list * ml_common_type
    |   SimpleType of unnamed_type
and ml_common_type =
		NoCommonBody
	|	TupleCommonBody of unnamed_type
and ml_type_name = string
and ml_type = ml_type_name * whitespace * ml_type_body * arbitrary_code_body
and arbitrary_code_body = code
and match_predicate = code
and match_term = match_pattern * whitespace * match_predicate
and match_pattern =
        VariableMatch of string * whitespace
    |   TagMatch of string * whitespace * (match_pattern list) * whitespace * match_pattern
    |   TupleMatch of whitespace * match_pattern list
    |   ThrowawayMatch of whitespace
    ;;


let rec extractWhitespace code =
	match code with
		Token(_) -> (code, "")
	|	Whitespace(w) -> (Whitespace(""), w)
	|	Sequence([]) -> (code,"")
	|	Sequence(h::t) -> (
			match (extractWhitespace(h),extractWhitespace(Sequence(t))) with
				((hC,hW),(Sequence(tC),tW)) -> (Sequence(hC :: tC), hW ^ " " ^ tW)
			)
	|	Type(_) -> (code,"")
	(* TODO BUG brax: whitespace could be hidden in here... *)
	|	MatchExpression(_) -> (code,"")
	;;
	
let rec
	makeCPPTypes opts =
		let regular, memoed = extractCPPs opts in
		CPPTypes(regular, memoed)
and
	extractCPPs opts =
		match opts with
			[] -> [],[]
		|	(a,b,c,NoMemo) :: tail -> (match extractCPPs tail with t1, t2 -> ((a,b,c) :: t1, t2))
		|	(a,b,c,Memo(w,code)) :: tail -> (match extractCPPs tail with t1, t2 -> (t1, ((a,b,c ^ w, code) :: t2)))
		;;

(* represents the current "scoping environment" - gives us enough information to fully qualify a type *)

type
	scope_envirionment =
		Root
	|	ClassOrNamespace of string * scope_envirionment
	|	Template of string * (template_term list) * scope_envirionment
	|	UnboundTemplate of (template_term list) * scope_envirionment
	;;

let rec
	fully_qualified_scope_prefix environment =
		match environment with
			Root -> "::"
		|	ClassOrNamespace(name, prior) -> (fully_qualified_scope_prefix prior) ^ name ^ "::"
		|	Template(name, terms, prior) -> (fully_qualified_scope_prefix prior) ^ name ^ " < " ^ (sep "," (function (qual, term,def) -> term) terms) ^ " > " ^ "::"
and
	fully_qualified_scope_name environment =
		match environment with
			Root -> ""
		|	ClassOrNamespace(name, prior) -> (fully_qualified_scope_prefix prior) ^ name
		|	Template(name, terms, prior) -> (fully_qualified_scope_prefix prior) ^ name ^ " < " ^ (sep "," (function (qual, term,def) -> term) terms) ^ " > "
and
	fully_qualified_name environment name =
		(fully_qualified_scope_prefix environment) ^ name
	;;

let add_class_scope scope classname =
	match scope with
		UnboundTemplate(terms, prior) -> Template(classname, terms, prior)
	|	_ -> ClassOrNamespace(classname, scope)
	;;
let add_template_scope scope terms = UnboundTemplate(terms, scope)
	;;
let rec
	scope_is_template scope =
		match scope with
			Root -> false
		|	ClassOrNamespace(n,prior) -> scope_is_template(prior)
		|	Template(s,l,e) -> true
		|	UnboundTemplate(s,e) -> true
		;;


(*

A very simple representation of the final C++.

We make the following additional rules:
	(1) within TemplatedScope, all cpp types get "typename" put in front of them
	(2) functions get defined inline inside of templates, but are placed at the end of the file otherwise.
			- member functions get the fully qualified typename placed in front

*)

type
    cpp_output = cpp_output_element list
and cpp_output_element =
        Text of string
    |   SeveralCPPEleements of cpp_output
    |   SourceWhitespace of string
    |   Block of cpp_output
    |   Private of cpp_output
    |   Public of cpp_output
    |   CPPType of string
    |   TemplatedScope of string * cpp_output
    |   Class of string * cpp_output
    |   FunctionDef of function_signature * function_preamble * function_body
	|	PostAmble of cpp_output
and function_signature =
		FreeFunction of string * string
	|	MemberFunction of bool * bool * cpp_output_element * string * string (* isStatic, isTemplate, return type, fullyqualified typename, name/sig *)
and function_body = cpp_output
and function_preamble = cpp_output
;;

(* code to render cpp_output to native C++ *)

(* makes "template<class T ...>" *)
let template_terms_to_template_def terms =
    match terms with
        [] -> ""
     |   _ -> "template < " ^ (sep "," (function (qual, term,def) -> qual ^ " " ^ term) terms) ^ " > ";;

(* makes "<T, ...>" *)
let template_terms_to_template_spec terms =
    match terms with
        [] -> ""
     |   _ -> " < " ^ (sep "," (function (qual, term,def) -> term) terms) ^ " > ";;

(* creates a Class or TemplatedScope object depending on the current scope *)
let class_creator template_terms (name, body) =
	match template_terms with
		[] -> Class(name, body)
	|	_ -> TemplatedScope((template_terms_to_template_def template_terms), Class(name, body) :: [])
	;;
let class_creator_fwd template_terms name =
	match template_terms with
		[] -> Text("class " ^ name ^ ";" ^ newline)
	|	_ -> Text((template_terms_to_template_def template_terms) ^ " class " ^ name ^ ";" ^ newline)
	;;
let stripRootScopeResolution qualname =
	if String.length qualname > 2 then
	if String.sub qualname 0 2 = "::" then
		String.sub qualname 2 ((String.length qualname) - 2)
		else
		qualname
		else
		qualname
	;;


let lastSubstringPlusOne to_find to_search = (
	try (Str.search_backward (Str.regexp_string to_find) to_search (String.length to_search)) + 1
	with | e -> 0		
	);;

let typenameKeywordIsNecessary name = (
	let lastDoubleColons = (lastSubstringPlusOne "::" ("   " ^ name)) in
	let lastCloseSharp = (lastSubstringPlusOne ">" ("   " ^ name)) in

	lastDoubleColons > 0 && lastDoubleColons > lastCloseSharp 
	)
	;;


(* function to make a fully qualified name for "name" in the root environment *)
let qualified_namer scope template_terms name =
	(fully_qualified_name scope name) ^ (template_terms_to_template_spec template_terms)
	;;

let rec cpp_output_to_string cppo =
      cpp_output_to_string_first false cppo
    ^ cpp_output_to_string_second false cppo
    ^ cpp_output_to_string_postamble cppo
and
    cpp_output_to_string_first inside_template cppo =
        String.concat "" (List.map (cpp_output_element_to_string_first inside_template) cppo)
and
    cpp_output_element_to_string_first inside_template cppo =
        match cppo with
            Text(s) -> s
        |   SeveralCPPEleements(o) -> cpp_output_to_string_first inside_template o
        |   SourceWhitespace(s) -> process_whitespace(s)
        |   Block(o) -> "\t{" ^ newline ^ tabify(cpp_output_to_string_first inside_template o) ^ newline ^ "\t}" ^ newline
        |   Class(name, body) -> "class " ^ name ^ " {" ^ newline ^ cpp_output_to_string_first inside_template body ^ newline ^ "};" ^ newline
        |   TemplatedScope(name, body) -> name ^ cpp_output_to_string_first true body
        |   CPPType(string) -> (if inside_template = true && (typenameKeywordIsNecessary string) then "typename " else "") ^ string
        |   Private(body) -> "private: " ^ newline ^ tabify(tabify(cpp_output_to_string_first inside_template body)) ^ newline
        |   Public(body) -> "public: " ^ newline ^ tabify(tabify(cpp_output_to_string_first inside_template body)) ^ newline
        |	FunctionDef(FreeFunction(rettype, s), prebody, body) ->
				" inline friend " ^
                rettype ^ " " ^ s ^
				 (let res = tabify(tabify((cpp_output_to_string_first inside_template prebody))) in if res = "" then "" else res ^ newline)
                        ^ "\t{" ^ newline ^ tabify( cpp_output_to_string_first inside_template body ) ^ newline ^ "\t}" ^ newline
		|	FunctionDef(MemberFunction(isStatic, isTemplate, rettype, qualName, s), prebody, body) ->
				if inside_template then
					(* we can go ahead and fully define the function *)
					(cpp_output_to_string_first inside_template (rettype :: [])) ^ " " ^ s ^
					(let res = tabify(tabify((cpp_output_to_string_first inside_template prebody))) in if res = "" then "" else res ^ newline)
						   ^ "\t{" ^ newline ^ tabify( cpp_output_to_string_first inside_template body ) ^ newline ^ "\t}" ^ newline
				else
					(* we're just forward declaring it *)
					(cpp_output_to_string_first inside_template (rettype :: [])) ^ " " ^ s ^ ";" ^ newline
		|	PostAmble(x) -> ""
and
    cpp_output_to_string_second inside_template cppo  =
        String.concat "" (List.map (cpp_output_element_to_string_second inside_template) cppo)
and
    cpp_output_element_to_string_second inside_template cppo =
        if inside_template = true then "" else
        match cppo with
            Text(s) -> ""
        |   SeveralCPPEleements(s) -> cpp_output_to_string_second inside_template s
        |   SourceWhitespace(s) -> ""
        |   Private(s) -> cpp_output_to_string_second inside_template s
        |   Public(s) -> cpp_output_to_string_second inside_template s
        |   CPPType(s) -> ""
        |   Block(o) -> cpp_output_to_string_second inside_template o
        |   TemplatedScope(name, body) -> cpp_output_to_string_second true body
        |   Class(name, body) -> cpp_output_to_string_second inside_template body
        |   FunctionDef(FreeFunction(rettype, s), prebody, body) -> ""
		|   FunctionDef(MemberFunction(isStatic, isTemplate, rettype, qualifiedName, s), prebody, body) ->
                    (if isTemplate then "" else " inline ") ^
					(cpp_output_to_string_first inside_template (rettype::[])) ^ " " ^ stripRootScopeResolution(qualifiedName) ^ " :: " ^ s ^ newline ^ (
						let res = tabify(tabify((cpp_output_to_string_first inside_template prebody))) in if res = "" then "" else res ^ newline)
                        ^ "\t{" ^ newline ^ tabify( cpp_output_to_string_first inside_template body ) ^ newline ^ "\t}" ^ newline
		|	PostAmble(x) -> ""
and
    cpp_output_to_string_postamble cppo =
		String.concat "" (List.map (cpp_output_to_string_element_postamble) cppo)
and
	cpp_output_to_string_element_postamble cppo =
        match cppo with
            Text(s) -> ""
        |   SeveralCPPEleements(s) -> cpp_output_to_string_postamble s
        |   SourceWhitespace(s) -> ""
        |   Private(s) -> cpp_output_to_string_postamble s
        |   Public(s) -> cpp_output_to_string_postamble s
        |   CPPType(s) -> ""
        |   Block(o) -> cpp_output_to_string_postamble o
        |   TemplatedScope(name, body) -> cpp_output_to_string_postamble body
        |   Class(name, body) -> cpp_output_to_string_postamble body
        |   FunctionDef(_, prebody, body) -> ((cpp_output_to_string_postamble prebody) ^ (cpp_output_to_string_postamble body))
		|	PostAmble(x) -> cpp_output_to_string x
		;;









(* functions to render resulting parse tree back into cpp_output *)



let rec
    	(* map the parse tree to cpp_output, keeping track of the current scoping *)

		code_to_cpp_output scope c =
            match c with
                    Token(t) -> Text(t) :: []
				|	Whitespace(w) -> SourceWhitespace(w) :: []
                |   Sequence([]) -> []
                |   Sequence(t :: t2) -> (code_to_cpp_output scope t) @ (code_to_cpp_output scope (Sequence(t2)))
				|   Grouping(TemplateScope(terms), code) -> TemplatedScope("", code_to_cpp_output (add_template_scope scope terms) (code)) :: []
                |   Grouping(ClassOrNamespaceScope(classname), body) -> code_to_cpp_output (add_class_scope scope classname) body
                |   Type(terms, mlt) -> (ml_type_list_to_cpp scope terms mlt)
				|   MatchExpression(t, expr, matchers ) -> matchers_to_cpp(t ^ "::self_type",expr,matchers)
    and

		(* render a particular ml_type group. operates in three parts: forward declarations, the main body, and then
			supplemental types (e.g. the common_data, alternative bodies, etc.) *)

	    ml_type_list_to_cpp scope template_terms mlt = 
				List.flatten(List.map (ml_type_class_def_forward scope template_terms) mlt)
			@	List.flatten(List.map (ml_type_class_def_body scope template_terms) mlt)
			@	List.flatten(List.map (ml_type_class_def_parts scope template_terms) mlt)
    and

		(*				renders a single type forward			*)

        ml_type_class_def_forward scope template_terms (name, wh0, mlt, arb_body_code) =
            (
                match mlt with
                        SimpleType(unnamed) -> (ml_tuple_class_forward scope template_terms name)
                    |   Alternatives(named_types, common) -> (ml_alternative_class_forward scope template_terms name named_types arb_body_code)
			)
	and

		(*				renders a single type body			*)

        ml_type_class_def_body scope template_terms (name, wh0, mlt, arb_body_code) =
            SourceWhitespace(wh0) :: [] @
			
			(
                match mlt with
                        SimpleType(unnamed) -> (ml_tuple_class_body scope template_terms (name, "", unnamed, arb_body_code))
                    |   Alternatives(named_types, common) ->
							List.flatten(List.map (ml_named_type_body_extract_whitespace scope template_terms name) named_types) @ 
							(ml_alternative_class_body scope template_terms name named_types common arb_body_code)
			)
	and
		(*				renders a single type's subparts			*)

		ml_type_class_def_parts scope template_terms (name, wh0, mlt, arb_body_code) =
            (
                match mlt with
                        SimpleType(unnamed) -> []
                    |   Alternatives(named_types, common) ->
                            List.flatten(List.map (ml_named_type_body scope template_terms name) named_types)
                            @  ml_type_common_data_class scope template_terms name named_types common :: []
                )
	and

		(*				Forward decls for Alternatives 				*)
		ml_alternative_class_forward scope template_terms name named_types arb_body_code =

			(* define a function to create classes in this environment *)
			let classmaker = class_creator_fwd template_terms in

			(classmaker(name ^ "_tags") ::
			classmaker(name ^ "_common_data") ::
			classmaker(name) ::
			[]) @
			(List.map (function nt -> match nt with
				NamedType(subname, wh1, unnamed, o, wh2) -> classmaker(name ^ "_" ^ subname ^ "Type")) named_types
				)

	and
		(*				Forward decls for Alternatives 				*)
		ml_tuple_class_forward scope template_terms name =

			(* define a function to create classes in this environment *)
			let classmaker = class_creator_fwd template_terms in

			classmaker(name) ::
			[]

	and
		generateEnumClassType classname enumtext = (
			"class " ^ classname ^ "{ public: " ^
			"typedef "^classname ^" self_type;" ^ 
			classname ^ "(int i) : m(i) {} " ^
			"bool operator==(const int& in) const { return m == in; } " ^
			"operator int () const { return m; } " ^
			"enum { "^ enumtext ^ "}; " ^ 
			"private: int m;" ^ 
			"};"
		)
	and
		(*				Bodies for Alternatives 				*)
		ml_alternative_class_body scope template_terms name named_types common arb_body_code =

			(* define a function to create classes in this environment *)
			let classmaker = class_creator template_terms in
			let fullyQualifiedNamer = qualified_namer scope template_terms in
			let ownFullName = fullyQualifiedNamer(name) in
			let commonTypes = (match common with TupleCommonBody(CPPTypes(c,mems)) -> c | NoCommonBody -> []) in
			let commonMemos = (match common with TupleCommonBody(CPPTypes(c, memos)) -> memos | NoCommonBody -> []) in


			let commaGlue a b = a ^ (if String.length(a) > 0 && String.length(b) > 0 then "," else "") ^ b in
			let commonConstructorArgs = if List.length(commonTypes) > 0 then (sep_with_indices "," (function(c, ix)-> "const member_" ^ string_of_int(ix) ^ "_type& common_" ^ string_of_int(ix)) commonTypes) else "" in
			let commonConstructorInitializers = if List.length(commonTypes) > 0 then (sep_with_indices "," (function(c, ix)-> "common_" ^ string_of_int(ix) ) commonTypes) else "" in
			let commonConstructorDefaultInits = if List.length(commonTypes) > 0 then (sep_with_indices "," (function(c, ix)-> "member_" ^ string_of_int(ix) ^ "_type()" ) commonTypes) else "" in
			
			let first_tag_name = (match named_types with NamedType(tag,_,_,_,_)::tail -> tag | _ -> "err") in
			
			let data_expr_from_tag constness_string tag =
					Text("mReference.getData( (" ^ tag ^ "Type*)0) ")
							:: []
				in
			
			let member_type_for ix = ownFullName ^ "::member_" ^ string_of_int(ix) ^ "_type" in
			let member_type_for_as_CPPType ix = CPPType(ownFullName ^ "::member_" ^ string_of_int(ix) ^ "_type") in
			let common_data_type_as_CPPType = CPPType(ownFullName ^ "::common_data_type &") in
            let const_common_data_type_as_CPPType = CPPType(ownFullName ^ "::common_data_type const& ") in

			classmaker(name,
				Public(
						Text("typedef ") :: CPPType(fullyQualifiedNamer(name)) :: Text(" self_type;" ^ newline)
					::	Text(generateEnumClassType "tag_type" (sep "," (function nt -> match nt with NamedType(name, wh1, unnamed, o, wh2) -> name) named_types))
					::  Text("typedef ::CPPML::TaggedUnionReference<self_type, void> tagged_union_reference_type;" ^ newline)
					::	Text("typedef ") :: CPPType(fullyQualifiedNamer(name ^ "_common_data")) :: Text(" common_data_type;" ^ newline)
					::  (map_with_indices (function((c,nm,w), ix)->
							SeveralCPPEleements(Text("typedef ") :: CPPType(c ^ " member_" ^ string_of_int(ix) ^ "_type") :: Text(";" ^ w ^ newline) :: [])
							) commonTypes) @
                        (map_with_indices (function((c,nm,w,def), ix)->
							SeveralCPPEleements(Text("typedef ") :: CPPType(c ^ " memo_member_" ^ string_of_int(ix) ^ "_type") :: Text(";" ^ w ^ newline) :: [])
							) commonMemos) @
						FunctionDef(MemberFunction(false, false, Text("const char*"), ownFullName, "tagName(void) const"), [], Text(
							(sep "" (
								function nt -> match nt with NamedType(tagname, wh1, unnamed, o, wh2) -> "if (this->mReference.getTag() == tag_type::" ^ tagname ^ ") return \"" ^ tagname ^ "\";"
								)
							named_types)
							^ " return \"\";"
								) ::
							[]
							) 
					::  FunctionDef(MemberFunction(false, false, CPPType(" ::CPPML::Refcount< " ^ ownFullName ^ ", void>::refcount_type"), ownFullName, "refcount(void) const"), [], Text("return this->mReference.getRefcount();") :: [])
					::  List.flatten(List.map (function n->
							match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
								Text("typedef ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text(" " ^ tag ^ "Type;" ^ newline) :: []
							) named_types)
					)
				::Public(
					(map_with_indices (
						function((c,nm,w), ix)->
							SeveralCPPEleements(
								Text("class getter_common_" ^ string_of_int(ix) ^ " { public: "
									^ " static const ")
							:: member_type_for_as_CPPType(ix)
							:: Text("& get(const self_type& s) { /* ASDF */ return s." ^ member_name_for(ix,nm) ^ "(); } " ^ " static ")
							:: member_type_for_as_CPPType(ix)
							:: Text("& get(self_type& s) { return s." ^ member_name_for(ix,nm) ^ "(); } " ^
									" static const char* name(void) { return \"" ^ member_name_for(ix,nm) ^ "\"; } " ^ " };" ^ newline)
							:: [])
							) commonTypes)
					)
				::Public(
					(map_with_indices (function((c,nm,w,def), ix)-> FunctionDef(
						MemberFunction(false,false,
							SeveralCPPEleements(
								Text("const ") :: 
									CPPType(ownFullName ^ "::memo_member_" ^ string_of_int(ix) ^ "_type&") :: 
									[]
								),
							ownFullName,
							(match nm with
									Unnamed -> "getMemo" ^ string_of_int(ix)
								|	Named(n) -> n)
							^ ("(void) const")
							),
						[],

						(Text("return mReference.getCommonData().memodata_m_" ^ string_of_int(ix) ^ ".get([&](){ return ") :: [])
						@ (code_to_cpp_output scope def) @ (Text("; });") :: [])
							)
						  )
						commonMemos)
					)
				::Public(map_with_indices (function(t, ix)->
					match t with NamedType(tag, wh1, unnamed_type, o, wh2) ->
					match unnamed_type with CPPTypes(cpp_types, memos) ->
						SeveralCPPEleements(
						Text("class getter_" ^ tag ^ " { public: "
							^ " static const ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& get(const self_type& s, bool check = true) { return s.get" ^ tag ^ "(check); } " ^ newline
							^ " static const ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& getConst(const self_type& s, bool check = true) { return s.get" ^ tag ^ "(check); } " ^ newline
							^ " static ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& getNonconst(self_type& s, bool check = true) { return s.get" ^ tag ^ "(check); } " ^ newline
							^ " static ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& get(self_type& s, bool check = true) { return s.get" ^ tag ^ "(check); } " ^ newline
							^ " static " ^ name ^ " constructor(" ^ (sep_with_indices "," (function((c,nm,w),ix)->"const " ^ c ^ "& in" ^ string_of_int(ix)) cpp_types) ^ ") {"
								^ "return self_type:: " ^ tag ^ "(" ^ (commaGlue commonConstructorDefaultInits (sep_with_indices "," (function((c,nm,w),ix)->"in" ^ string_of_int(ix)) cpp_types)) ^ "); }" ^ newline
							^ " static bool is(const self_type& s) { return s.is" ^ tag ^ "(); } " ^ newline
							^ " static const char* name(void) { return \"" ^ tag ^ "\"; } " ^ newline
							^ " };" ^ newline)
							:: []
							)
							) named_types)

				::Public(
						Text("typedef ::CPPML::Kinds::alternative kind;" ^ newline )
					:: Text("typedef ") ::
						metadata_to_chain(
							(
							map_with_indices (function(t, ix)->
								match t with NamedType(tag, wh1, unnamed_type, o, wh2) ->
									SeveralCPPEleements(Text(" ::CPPML::Alternative< self_type , ") ::
										CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text(" , "
										^ " getter_" ^ tag
										^ " > ") :: []
										)
									) named_types
							)
							@
							(
							map_with_indices (
								function(t, ix)->
									Text(" ::CPPML::AlternativeCommonMember< self_type, "
										^ "self_type::member_" ^ string_of_int(ix) ^ "_type, "
										^ "getter_common_" ^ string_of_int(ix) ^ ", "
										^ string_of_int(ix)
										^ " > "
										)
									)
								commonTypes
							)
						)
						:: Text(" metadata;")
					:: []
					)
				::Private(
						Text("tagged_union_reference_type mReference;" ^ newline)
					::  FunctionDef(MemberFunction(false, false, Text("void"), ownFullName, "drop(void)"), [],
							Text("if (mReference.decrementRefcount()) {"^newline^"\t") ::
							Text("switch (mReference.getTag()) ") ::
							Block(
								List.map (
									function n->
									match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
										SeveralCPPEleements(
											Text("case tag_type::" ^ tag ^ " : mReference.destroyAs(( ")
											:: CPPType(
												fullyQualifiedNamer(name ^ "_"  ^tag^"Type"))
											:: Text(" *)0); break; " ^ newline)
											:: []
										)
									) named_types
								) ::
							Text(newline ^ "\t}") ::
							[]
							)
					:: []
					)
				::Public(
						FunctionDef(MemberFunction(true, true, Text("template<class funtype__> void"), ownFullName, " callback(const funtype__& inFunc, tag_type inTag) const"), [],
							Text("switch (inTag) ") ::
							Block(
								List.map (
									function n->
									match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
										SeveralCPPEleements(
											Text("case tag_type::" ^ tag ^ " : inFunc(( ")
											:: CPPType(
												fullyQualifiedNamer(name ^ "_"  ^tag^"Type"))
											:: Text(" *)0); break; " ^ newline)
											:: []
										)
									) named_types
								) ::
							[]
							)
					:: []
					)
				::Public(
						FunctionDef(MemberFunction(false, true, Text("template<class subtype__> const subtype__&"), ownFullName, " get(subtype__* deliberatelyZero) const"), [],
							Text("return mReference.getData(deliberatelyZero);") :: []
							)
					:: []
					)
				::Public(
						FunctionDef(MemberFunction(false, true, Text("template<class subtype__> subtype__&"), ownFullName, " get(subtype__* deliberatelyZero)"), [],
							Text("return mReference.getData(deliberatelyZero);") :: []
							)
					:: []
					)
				::Public(
						FunctionDef(MemberFunction(false, true, Text("template<class funtype__> void "), ownFullName, " visit(const funtype__& inFunc) const"), [],
							Text("switch (mReference.getTag()) ") ::
							Block(
								List.map (
									function n->
									match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
										SeveralCPPEleements(
											Text("case tag_type::" ^ tag ^ " : inFunc(mReference.getData(( ")
											:: CPPType(
												fullyQualifiedNamer(name ^ "_"  ^tag^"Type"))
											:: Text(" *)0)); break; " ^ newline)
											:: []
										)
									) named_types
								) ::
							[]
							)
					:: []
					)
				::Private(
						FunctionDef(MemberFunction(false, false, Text("/*pointer constructor*/"), ownFullName, name ^ "(const tagged_union_reference_type in)"), [],
							Text("mReference = in;") :: [])
					::  []
					)
				::Public(
						FunctionDef(MemberFunction(false, false, Text(""), ownFullName,"~" ^ name ^ "()"), [], Text("drop();") :: [])
					::	FunctionDef(
							MemberFunction(
								false,
								false,
								Text("/*empty constructor*/"),
								ownFullName,
								name ^ "()"
								),
							[],
							Text("mReference = tagged_union_reference_type::create(" ^
								"tag_type::" ^ first_tag_name ^ "," ^
								"common_data_type(" ^ (commaGlue commonConstructorDefaultInits "") ^ "), " ^
								first_tag_name ^ "Type()" ^
								");") :: []
							)
					::	FunctionDef(MemberFunction(false, false, common_data_type_as_CPPType, ownFullName, "getCommonData(void) const"), [],
							Text("return mReference.getCommonData();") :: [])
					::	FunctionDef(MemberFunction(false, false, const_common_data_type_as_CPPType, ownFullName, "getCommonData(void)"), [],
							Text("return mReference.getCommonData();") :: [])
					::	FunctionDef(MemberFunction(false, false, Text("/*copy constructor*/"), ownFullName, name ^ "(const self_type& in)"), [],
							Text("mReference = in.mReference; mReference.incrementRefcount();") :: [])
					::	FunctionDef(MemberFunction(false, false, Text("/*copy constructor*/"), ownFullName, name ^ "(self_type&& in)"), [],
							Text("mReference.swap(in.mReference);") :: [])
					
					::  FunctionDef(MemberFunction(false, false, CPPType(ownFullName ^ "&"), ownFullName, "operator=(const self_type& in)"), [],
							Text("in.mReference.incrementRefcount(); tagged_union_reference_type newRef =in.mReference; drop(); mReference = newRef; return *this;") :: [])
					::  FunctionDef(MemberFunction(false, false, CPPType(ownFullName ^ "&"), ownFullName, "operator=(self_type&& in)"), [],
							Text("mReference.swap(in.mReference); return *this;") :: [])
					::  List.map (function n->
						match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
							FunctionDef(
								MemberFunction(
									false,
									false,
									Text("/*constructor no common*/"),
									ownFullName,
									name ^ "(" ^ (commaGlue commonConstructorArgs ("const " ^ tag ^ "Type& in")) ^ ")"
									),
								[],
								Text("mReference = tagged_union_reference_type::create(" ^
									"tag_type::" ^ tag ^ "," ^
									"common_data_type(" ^ (commaGlue commonConstructorInitializers "") ^ "), " ^
									"in" ^
									");")
								:: []
								)
						) named_types
					@ List.map (function n->
						match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
							FunctionDef(
								MemberFunction(
									false,
									false,
									Text("/*constructor with common*/"),
									ownFullName,
									name ^ "(" ^ ("const " ^ tag ^ "Type& in, const common_data_type& inCommon") ^ ")"
									),
								[],
								Text("mReference = tagged_union_reference_type::create(" ^
									"tag_type::" ^ tag ^ "," ^
									"inCommon, " ^
									"in" ^
									");")
								:: []
								)
						) named_types
					@ (if String.length(commonConstructorArgs) > 0 then
						List.map (function n->
						match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
							FunctionDef(
								MemberFunction(
									false,
									false,
									Text("/*constructor with move semantics no common*/"),
									ownFullName,
									name ^ "(" ^ tag ^ "Type&& in)"
									),
								[],
								Text("mReference = tagged_union_reference_type::create(" ^
									"tag_type::" ^ tag ^ "," ^
									"common_data_type(" ^ (commaGlue commonConstructorDefaultInits "") ^ "), " ^
									"::CPPML::forward<" ^ tag ^"Type>(in)" ^
									");")
								:: []
								)
						) named_types
						else []
						) 
					@ (if String.length(commonConstructorArgs) > 0 then
						List.map (function n->
						match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
							FunctionDef(
								MemberFunction(
									false,
									false,
									Text("/*constructor with move semantics with common*/"),
									ownFullName,
									name ^ "(" ^ tag ^ "Type&& in, common_data_type&& inCommon)"
									),
								[],
								Text("mReference = tagged_union_reference_type::create(" ^
									"tag_type::" ^ tag ^ "," ^
									"::CPPML::forward<common_data_type>(inCommon), " ^
									"::CPPML::forward<" ^ tag ^"Type>(in)" ^
									");")
								:: []
								)
						) named_types
						else []
						)
					@ (if String.length(commonConstructorArgs) > 0 then
						List.map (function n->
						match n with NamedType(tag, wh1, unnamed_type, o, wh2) ->
							FunctionDef(
								MemberFunction(
									false,
									false,
									Text("/*constructor 2*/"),
									ownFullName,
									name ^ "(const " ^ tag ^ "Type& in)"
									),
								[],
								Text("mReference = tagged_union_reference_type::create(" ^
									"tag_type::" ^ tag ^ "," ^
									"common_data_type(" ^ (commaGlue commonConstructorDefaultInits "") ^ "), " ^
									"in" ^
									");")
								:: []
								)
						) named_types
						else []
						)
					@(map_with_indices  (function((c,nm,w), ix)->
						FunctionDef(
							MemberFunction(
								false,
								false,
								Text("const " ^ member_type_for(ix) ^ "&  "),
								ownFullName,
								member_name_for(ix, nm) ^ "(void) const"
								),
							[],
							Text("return mReference.getCommonData().m_" ^ string_of_int(ix) ^ ";" ^ newline) :: [])
							)
						commonTypes
						)
                    @(map_with_indices (
						function((c,nm,w), ix) ->
							FunctionDef(
								MemberFunction(false, false, Text(member_type_for(ix) ^ "&  "),  ownFullName, member_name_for(ix, nm) ^ "(void)"),
								[],
								Text("return mReference.getCommonData().m_" ^ string_of_int(ix) ^ ";" ^ newline) :: []
								)
							) commonTypes
						)
					@(map_with_indices  (
						function((c,nm,w), ix) ->
							FunctionDef(
								MemberFunction(false, false, Text("const " ^ member_type_for(ix) ^ "&  "), ownFullName, "getM" ^ string_of_int(ix) ^ "(void) const"),
								[],
								Text("return mReference.getCommonData().m_" ^ string_of_int(ix) ^ ";" ^ newline) :: []
								)
							) commonTypes
						)
					)
				::Public(
					List.flatten(List.map (function t ->
						match t with NamedType(tag, wh1, unnamed_type, o, wh2) ->
						match unnamed_type with CPPTypes(cpp_types, memos) ->
								Text("/*static constructor*/ static ")
									:: FunctionDef(MemberFunction(false, false, CPPType(ownFullName), ownFullName, tag ^ "("^ (commaGlue commonConstructorArgs (sep_with_indices "," (function((c,nm,w),ix)->"const " ^ c ^ "& in" ^ string_of_int(ix)) cpp_types)) ^")"),
									[], Text("return self_type(tagged_union_reference_type::create(tag_type::" ^ tag ^ ", common_data_type(" ^
											(commaGlue commonConstructorInitializers "") ^ "), " ^ 
											( (tag ^ "Type(" ^ (sep_with_indices "," (function((c,nm,w),ix)->"in" ^ string_of_int(ix)) cpp_types) ^ ")")) ^ "));") :: []
									)
							::  SeveralCPPEleements(
								if String.length(commonConstructorArgs) > 0 then
									Text("/*static constructor without common*/ static ")
									::  FunctionDef(
												MemberFunction(false, false, CPPType(ownFullName), ownFullName, tag ^ "("^ 
														(sep_with_indices "," (function((c,nm,w),ix)->"const " ^ c ^ "& in" ^ string_of_int(ix)) cpp_types) ^")"),
											[], Text("return self_type(tagged_union_reference_type::create(tag_type::" ^ tag ^ ", common_data_type(" ^ (commaGlue commonConstructorDefaultInits "") ^ "), " ^ 
													( (tag ^ "Type(" ^ (sep_with_indices "," (function((c,nm,w),ix)->"in" ^ string_of_int(ix)) cpp_types) ^ ")")) ^ "));") :: []
											) :: []
								else
									[]
								)
							::  FunctionDef(MemberFunction(false, false, SeveralCPPEleements(Text("const ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& ") :: []), ownFullName, "get" ^ tag ^ "(void) const"), [],
									Text("return ") :: (data_expr_from_tag "const" tag) @ (Text(";")::[]))
							::  FunctionDef(MemberFunction(false, false, SeveralCPPEleements(CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type"))::Text("& ") :: []), ownFullName, "get" ^ tag ^ "(void)"), [],
									Text("return ") :: (data_expr_from_tag "" tag) @ (Text(";")::[]))
							::  FunctionDef(MemberFunction(false, false, SeveralCPPEleements(Text("const ") :: CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& "):: []), ownFullName, "get" ^ tag ^ "(bool check) const"), [],
									Text("if (check && !this->is" ^ tag ^ "()) CPPML::throwBadUnionAccess(*this); ")
										:: Text("return ") :: (data_expr_from_tag "const" tag) @ (Text(";")::[]))
							::  FunctionDef(MemberFunction(false, false, SeveralCPPEleements(CPPType(fullyQualifiedNamer(name ^ "_" ^ tag ^ "Type")) :: Text("& ") :: []), ownFullName, "get" ^ tag ^ "(bool check)"), [],
									Text("if (check && !this->is" ^ tag ^ "()) CPPML::throwBadUnionAccess(*this);")
										:: Text("return ") :: (data_expr_from_tag "" tag) @ (Text(";")::[]))
							::  FunctionDef(MemberFunction(false, false, Text("bool"), ownFullName, "is" ^ tag ^ "(void) const"), [], Text("return mReference.getTag() == tag_type::" ^ tag ^ ";") :: [])
							:: match o with
									NoTypeOp -> Text("") :: []
								|   TypeOp(o) ->
										FunctionDef(
											FreeFunction(name, " operator" ^ o ^ "("^ (sep_with_indices "," (function((c,nm,w),ix)->"const " ^ c ^ "& in" ^ string_of_int(ix)) cpp_types) ^")"),
											[],
												Text("return ") :: Text("self_type") :: Text("::" ^ tag ^ "(" ^ (sep_with_indices "," (function((c,nm,w),ix)->"in" ^ string_of_int(ix)) cpp_types) ^ ");")
											:: []
											)
									::  []
						) named_types)
					)
				::Private(code_to_cpp_output scope arb_body_code)

				::  []
				)
			:: []
    and
        ml_type_common_data_class scope template_terms name named_types common =

			(* define a function to create classes in this environment *)
			let classmaker = class_creator template_terms in
			let fullyQualifiedNamer = qualified_namer scope template_terms in
			let ownFullName = fullyQualifiedNamer (name ^ "_common_data") in
			let commonTypes = (match common with TupleCommonBody(CPPTypes(c, memos)) -> c | NoCommonBody -> []) in
			let commonMemos = (match common with TupleCommonBody(CPPTypes(c, memos)) -> memos | NoCommonBody -> []) in

			let commonConstructorArgs =
				if List.length(commonTypes) > 0 then
					(sep_with_indices "," (function(c, ix)-> "const member_" ^ string_of_int(ix) ^ "_type& in" ^ string_of_int(ix)) commonTypes)
				else ""
				in
			let commonConstructorInitializers =
				if List.length(commonTypes) > 0 then
					":" ^ (sep_with_indices "," (function(c, ix)-> "m_" ^ string_of_int(ix) ^ "(" ^ "in" ^ string_of_int(ix) ^ ")") commonTypes)
				else ""
				in
			let commonConstructorInitializersFromCopyConstructorArg =
				if List.length(commonTypes) > 0 then
					":" ^ (sep_with_indices "," (function(c, ix)-> "m_" ^ string_of_int(ix) ^ "(" ^ "inToCopy.m_" ^ string_of_int(ix) ^ ")") commonTypes)
				else ""
				in
			classmaker(name ^ "_common_data",
                Public(
                        Text("typedef ") :: CPPType(fullyQualifiedNamer(name)) :: Text(" holding_type;" ^ newline)
                    ::  (map_with_indices (function((c,nm,w), ix)-> Text("typedef " ^ c ^ " member_" ^ string_of_int(ix) ^ "_type;" ^ w ^ newline)) commonTypes) @
                        (map_with_indices (function((c,nm,w,def), ix)-> SeveralCPPEleements(Text("typedef ") :: CPPType(c) :: Text(" memo_member_" ^ string_of_int(ix) ^ "_type;" ^ w ^ newline) :: [])) commonMemos) @
                        (map_with_indices (function((c,nm,w,def), ix)-> 
                        		SeveralCPPEleements(Text("typedef ") :: CPPType("::CPPML::MemoStorage<holding_type, memo_member_" ^ string_of_int(ix) ^ "_type, void>") :: 
                        			Text(" memo_member_storage_" ^ string_of_int(ix) ^ "_type;" ^ w ^ newline) :: [])) commonMemos
                    		) @
						FunctionDef(
								MemberFunction(
									false,
									false,
									Text(" /* common data constructor with individual arguments */ "),
									ownFullName,
									name ^ "_common_data(" ^ commonConstructorArgs ^ ")"
									),
								Text(commonConstructorInitializers) :: [],
								(* initialize the memovalues *)
								[]
								)
							::
                        FunctionDef(
								MemberFunction(
									false,
									false,
									Text(" /* common data copy constructor */ "),
									ownFullName,
									name ^ "_common_data(const " ^ name ^ "_common_data& inToCopy)"
									),
								Text(commonConstructorInitializersFromCopyConstructorArg) :: [],
								(* initialize the memovalues *)
								[]
								)
							:: 
						FunctionDef(MemberFunction(false, false, Text(" /* common_data destructor */"),
                                        ownFullName, "~" ^ name ^ "_common_data()"), [],
							[]
							)
						::[]
                    )
				(* allocate the common types *)
				:: Public(
                    map_with_indices (
                        function((c,nm,w), ix)->
                            Text("member_" ^ string_of_int(ix) ^ "_type m_" ^ string_of_int(ix) ^ ";" ^ newline))
                        commonTypes
                    )
				:: Public(
                    map_with_indices (
						(* define the typedefs for the various memo objects *)
                        function((c,nm,w,def), ix)->
                            Text("mutable memo_member_storage_" ^ string_of_int(ix) ^ "_type memodata_m_" ^ string_of_int(ix) ^ ";" ^ newline)
							)
                        commonMemos
                    )
                ::[]
                )
    and
        member_name_for (ix, membername) =
            match membername with
                Unnamed -> "m" ^ string_of_int(ix)
            |   Named(s) -> s
    and
        ml_tuple_class_body scope template_terms (tag, suffix, unnamed_types, arb_body_code) =
            (
			let classmaker = class_creator template_terms in
			let fullyQualifiedNamer = qualified_namer scope template_terms in
			let ownFullName = fullyQualifiedNamer (tag ^ suffix) in
			let member_type_for ix = ownFullName ^ "::member_" ^ string_of_int(ix) ^ "_type" in
			
            match unnamed_types with CPPTypes(cpp_types, memos) ->
                classmaker( tag ^ suffix,
                    Public(
                            Text("typedef " ^ tag ^ suffix ^ " self_type;" ^ newline)
                        ::  (map_with_indices (function((c,nm,w), ix)-> Text("typedef " ^ c ^ " member_" ^ string_of_int(ix) ^ "_type;" ^ w ^ newline)) cpp_types)
                        @ (FunctionDef(MemberFunction(false, false, Text(""), ownFullName, "/*tuple constructor*/ " ^ tag ^ suffix ^ "(" ^ (sep_with_indices "," (function(c, ix)-> "const member_" ^ string_of_int(ix) ^ "_type& in" ^ string_of_int(ix)) cpp_types) ^ ") "),
                                Text(if List.length(cpp_types) > 0 then ":" ^ (sep_with_indices "," (function(c, ix)-> "m_" ^ string_of_int(ix) ^ "(" ^ "in" ^ string_of_int(ix) ^ ")") cpp_types) else "") ::
								[],
                                Text("::CPPML::validate(*this);") :: []) :: [])
						@ (
						(* empty constructor for tuple types *)
                        match cpp_types with
							h::t->
								FunctionDef(MemberFunction(false, false, Text(""), ownFullName, "/* empty tuple constructor */ " ^ tag ^ suffix ^ "() "),
									Text(if List.length(cpp_types) > 0 then ":" ^ (sep_with_indices "," (function(c, ix)-> "m_" ^ string_of_int(ix) ^ "(member_" ^ string_of_int(ix) ^ "_type())") cpp_types) else "") ::
									[],
									Text("::CPPML::validate(*this);") :: []
								)	:: []
							| [] -> []
						)
						@
                        FunctionDef(MemberFunction(false, false, Text(""), ownFullName, tag ^ suffix ^ "(const " ^ tag ^ suffix ^ "& in) "),
                            Text((if List.length(cpp_types) > 0 then ":" ^ (sep_with_indices "," (function((c,nm,w), ix)-> "m_" ^ string_of_int(ix) ^ "(" ^ "in.m_" ^ string_of_int(ix) ^ ")") cpp_types) else ""))::[],
                            [])
                        :: FunctionDef(MemberFunction(false, false, CPPType(fullyQualifiedNamer(tag ^ suffix) ^ "& "), ownFullName, "operator=(const " ^ tag ^ suffix ^ "& in)"),
                            [],
                                Text(sep_with_indices "" (function((c,nm,w), ix)-> "m_" ^ string_of_int(ix) ^ " = " ^ "in.m_" ^ string_of_int(ix) ^ ";" ^ newline) cpp_types)
                            ::  Text("return *this;" ^ newline)
                            :: [])
						:: FunctionDef(MemberFunction(true, false, Text("const char* "), ownFullName, "nameForMember(long ix)"),
							[],
                                Text(sep_with_indices "" (function((c,nm,w), ix)-> "if (ix == " ^ string_of_int(ix) ^ ") return \"" ^ member_name_for(ix,nm) ^ "\";" ^ newline) cpp_types)
                            ::  Text("return \"\";" ^ newline)
                            :: []
							)
						:: FunctionDef(MemberFunction(false, true, Text("/** tuple visit function **/ template<class funtype__> void "), ownFullName, "visitWithGetter_(const funtype__& F) const"),
							[],
                                Text(sep_with_indices "" (function((c,nm,w), ix)-> "F(m_" ^ string_of_int(ix) ^ ", getter_" ^ string_of_int(ix) ^"());" ^ newline) cpp_types)
                            :: []
							)
						:: FunctionDef(MemberFunction(false, true, SeveralCPPEleements(Text("/** tuple transformation function **/ template<class funtype__> ") :: CPPType(ownFullName) :: []), ownFullName, "transform_(const funtype__& F) const"),
							[],
								Text("return self_type(") :: 
                                Text(sep_with_indices "," (function((c,nm,w), ix)-> "F(m_" ^ string_of_int(ix) ^ ")") cpp_types)
							::	Text(");")
                            :: []
							)
                        ::(map_with_indices (function((c,nm,w), ix)-> SeveralCPPEleements(
							Text("class getter_" ^ string_of_int(ix) ^ " { public: "
							^ " static const ") :: CPPType(member_type_for(ix)) :: Text("& get(const self_type& s) { return s." ^ member_name_for(ix,nm) ^ "(); } "
							^ " static ") :: CPPType(member_type_for(ix)) :: Text("& get(self_type& s) { return s." ^ member_name_for(ix,nm) ^ "(); } "
							^ " static const char* name(void) { return \"" ^ member_name_for(ix,nm) ^ "\"; } "
							^ " };" ^ newline) :: []
							)) cpp_types)
						@(map_with_indices  (function((c,nm,w), ix)-> FunctionDef(MemberFunction(false, false, SeveralCPPEleements(Text("const ") :: CPPType(member_type_for(ix)) :: Text("&  ") :: []), ownFullName, member_name_for(ix, nm) ^ "(void) const"), [], Text("return m_" ^ string_of_int(ix) ^ ";" ^ newline) :: [])) cpp_types)
                        @(map_with_indices  (function((c,nm,w), ix)-> FunctionDef(MemberFunction(false, false, SeveralCPPEleements(Text("      ") :: CPPType(member_type_for(ix)) :: Text("&  ") :: []),  ownFullName, member_name_for(ix, nm) ^ "(void)"), [], Text("return m_" ^ string_of_int(ix) ^ ";" ^ newline):: [])) cpp_types)
                        @(map_with_indices  (function((c,nm,w), ix)-> FunctionDef(MemberFunction(false, false, SeveralCPPEleements(Text("const ") :: CPPType(member_type_for(ix)) :: Text("&  ") :: []), ownFullName, "getM" ^ string_of_int(ix) ^ "(void) const"), [], Text("return m_" ^ string_of_int(ix) ^ ";" ^ newline):: [])) cpp_types)
                        )
                :: Private(
                    map_with_indices (
                        function((c,nm,w), ix)->
                            Text("member_" ^ string_of_int(ix) ^ "_type m_" ^ string_of_int(ix) ^ ";" ^ newline))
                        cpp_types
                    )
                ::Private(code_to_cpp_output scope arb_body_code)
                ::Public(
					Text("typedef ::CPPML::Kinds::tuple kind;" ^ newline )
					:: Text("typedef ") ::
						(metadata_to_chain (map_with_indices (
							function((c,nm,w), ix)->
								Text(" ::CPPML::TupleMember< self_type , "
									^ " member_" ^ string_of_int(ix) ^ "_type , "
									^ " getter_" ^ string_of_int(ix) ^ " , "
									^ " " ^ string_of_int(ix) ^ " "
									^ " > "
									)
								)
							cpp_types
							)
						) :: Text(" metadata;") :: []
					)
				:: []
                ) :: []
            )
	and
		metadata_to_chain metas =
			match metas with
				[] -> Text("::CPPML::Null")
			| a :: b -> SeveralCPPEleements(Text("::CPPML::Chain< ") :: a :: Text(" , ") :: metadata_to_chain(b) :: Text(" > ") :: [])
    and
        ml_named_type_body scope template_terms  alternative_name named_t =
            match named_t with
                NamedType(tag, wh1, unnamed_type, o, wh2) ->
                match unnamed_type with CPPTypes(cpp_types, memos) ->
                      (ml_tuple_class_body scope template_terms (alternative_name ^ "_" ^ tag, "Type", unnamed_type, Token("")))
    and
        ml_named_type_body_extract_whitespace scope template_terms  alternative_name named_t =
            match named_t with
                NamedType(tag, wh1, unnamed_type, o, wh2) ->
                match unnamed_type with CPPTypes(cpp_types, memos) ->
                      SourceWhitespace(wh1) :: SourceWhitespace(wh2)  :: []
    and
        match_validate (term, varname, extension, vartype) =
            match term with
                VariableMatch(s, wh) -> Text("true") :: SourceWhitespace(wh) :: []
            |   ThrowawayMatch(wh) -> Text("true") :: SourceWhitespace(wh) :: []
            |   TagMatch(tagname, wh, submatches, wh2, commonMatch) ->
                    Text("(" ^ varname ^ extension ^ ".is" ^ tagname ^ "() ") :: SourceWhitespace( wh ) ::
                    List.flatten(map_with_indices (function (subterm, ix)->
                                Text(newline ^ " && (") :: []
                            @  match_validate(subterm, varname, extension ^ ".get" ^ tagname ^ "()" ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: " ^ tagname ^ "Type" ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                            @  Text(")")
                            ::  []
                            ) submatches)
					@ Text("&& ") :: match_validate(commonMatch, varname, extension, vartype)
                    @  (Text(")")
                    :: SourceWhitespace(wh2)
                    :: []
					 )
            |   TupleMatch(wh, submatches) ->
                    (
                    SourceWhitespace(wh) :: Text("( true ") ::
                        List.flatten(map_with_indices (function (subterm, ix)->
                                Text(newline ^ "&& (") :: []
                            @   match_validate(subterm, varname, extension ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                            @   Text(")")
                            ::  []
                            ) submatches)
                    @ Text(")") :: []
                    )
    and
		interleaveIntoCPPList (l, toInterleave) = (
			match l with
				[] -> []
			|	x :: [] -> x :: []
			|	x :: tail -> x :: toInterleave :: (interleaveIntoCPPList (tail, toInterleave))
		)
	and
        match_variable_bind(term, varname, extension, vartype) =
            match term with
                VariableMatch(s,w) -> Text("const ") :: CPPType(vartype ^ "& ") :: Text(s ^ "(" ^ varname ^ extension ^ ");" ^ newline) :: []
            |   ThrowawayMatch(w) -> Text("") :: []
            |   TagMatch(tagname, w1, submatches, w2, commonMatch) ->
                    List.flatten(
                        map_with_indices (function (subterm, ix)->
                            match_variable_bind(subterm, varname, extension ^ ".get" ^ tagname ^ "()" ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: " ^ tagname ^ "Type" ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                            ) submatches
					) @ (
					match_variable_bind(commonMatch, varname, extension, vartype)
					)
            |   TupleMatch(wh, submatches) ->
                  SourceWhitespace(wh) ::
                    List.flatten(
                    map_with_indices (function (subterm, ix)->
                        match_variable_bind(subterm, varname, extension ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                        ) submatches
                    )
    and
        match_variable_bind_whitespace(term) =
            match term with
                VariableMatch(s,w) -> SourceWhitespace(w) :: []
            |   ThrowawayMatch(w) -> SourceWhitespace(w) :: []
            |   TagMatch(tagname, w1, submatches, w2, commonMatch) ->
                    (
					SourceWhitespace(w1) :: SourceWhitespace(w2) :: 
					List.flatten(
						map_with_indices (function (subterm, ix)->
							match_variable_bind_whitespace(subterm)
							) submatches
							) @ 
						match_variable_bind_whitespace commonMatch
					)
            |   TupleMatch(wh, submatches) ->
                    SourceWhitespace(wh) :: 
					List.flatten(
                    map_with_indices (function (subterm, ix)->
                        match_variable_bind_whitespace subterm
                        ) submatches
                    )
	and
        match_variable_bind_types(term, varname, extension, vartype) =
            match term with
                VariableMatch(s,w) -> SeveralCPPEleements(Text("const ") :: Text(vartype ^ "& ") :: Text(s) :: []) :: []
            |   ThrowawayMatch(w) -> []
            |   TagMatch(tagname, w1, submatches, w2, commonMatch) ->
                    (
					List.flatten(
						map_with_indices (function (subterm, ix)->
							match_variable_bind_types(subterm, varname, extension ^ ".get" ^ tagname ^ "()" ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: " ^ tagname ^ "Type" ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
							) submatches
							) @ 
						match_variable_bind_types (commonMatch, varname, extension, vartype)
					)
            |   TupleMatch(wh, submatches) ->
                    List.flatten(
                    map_with_indices (function (subterm, ix)->
                        match_variable_bind_types(subterm, varname, extension ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                        ) submatches
                    )
	and
        match_variable_bind_args(term, varname, extension, vartype) =
            match term with
                VariableMatch(s,w) -> Text("(" ^ varname ^ extension ^ ")" ^ newline) :: []
            |   ThrowawayMatch(w) -> []
            |   TagMatch(tagname, w1, submatches, w2, commonMatch) ->
                    (
					List.flatten(
						map_with_indices (function (subterm, ix)->
							match_variable_bind_args(subterm, varname, extension ^ ".get" ^ tagname ^ "()" ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: " ^ tagname ^ "Type" ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
							) submatches
						) @ match_variable_bind_args(commonMatch, varname, extension, vartype)
					)
            |   TupleMatch(wh, submatches) ->
                    List.flatten(
                    map_with_indices (function (subterm, ix)->
                        match_variable_bind_args(subterm, varname, extension ^ ".getM" ^ string_of_int(ix) ^ "()", vartype ^ " :: member_" ^ string_of_int(ix) ^ "_type" )
                        ) submatches
                    )
    and
        statement_matchexpose varname vartype (match_term, wh, match_predicate) =
                Text("if (") :: []
            @   match_validate(match_term, varname, "", vartype)
            @   Text(") {") :: SourceWhitespace(wh)
					:: match_variable_bind(match_term, varname, "", vartype)
			@	(
			 	((code_to_cpp_output Root match_predicate) @ Text("; } else ") :: [])
			)
	and
		flattenCSLElt l =
			match l with
				Token(_) -> l :: []
			|	Whitespace(_) -> l :: []
			|	Sequence(subs) -> flattenCSL subs
			|	Grouping(_) -> l :: []
			|	Type(_,_)->l :: []
			|	MatchExpression(_,_,_) -> l :: []
	and
		flattenCSL l = List.flatten (List.map flattenCSLElt l)
    and
		(* render a match expression using a c++ lambda function *)
        matchers_to_cpp (t, expr, matchers) =
			match matchers with
				[] -> (
					Text("throw ::CPPML::matchError(") :: (code_to_cpp_output Root expr) @ Text(")") :: []
					)
			|	(_,_,firstMatchPredicate) :: tail -> (
					statement_matchers_to_cpp (t, expr, matchers)
					)
	and
		statement_matchers_to_cpp (t,expr,matchers) = (
			let matchname = cppmlMatchVariableName "curmatch__" in
            (	Text("{ auto ") :: Text(matchname ^ "__(::CPPML::grabMatchValue(") :: 
				(code_to_cpp_output Root expr) @ Text("));") ::
				Text("const auto& " ^ matchname ^ "(" ^ matchname ^ "__.m" ^ ");") ::
				[])
            @ List.flatten(List.map (statement_matchexpose matchname t) matchers)
            @ Text("{ throw CPPML::matchError(" ^ matchname ^ ");  } }") :: []
		)
    ;;
let preamble = (
	let fpreamble = Util.file_contents (Util.relativePath "preamble.txt") in
	if noPreamble then "" else
	if guardedPreamble then
		"#ifndef CPPML_preamble_hpp_________\n" ^ 
		"#define CPPML_preamble_hpp_________\n" ^
		fpreamble ^ "\n" ^ 
		"#endif\n"
	else
		fpreamble
	);;
let rec
		code_to_cpp_whole_file c = preamble ^ code_to_cpp c
    and code_to_cpp c = cpp_output_to_string (code_to_cpp_output Root c)
	;;
