/* File parser.mly */

%token <string> TOKEN
%token <string> WHITESPACE
%token <string> IDENT
%token SCOPE GT LT AS CLASS PUBLIC PRIVATE
%token MATCH_BECOMES TYPE COMMA SEMI EQ AND OF MATCH MINUSPIPE WITH CONST STAR AMP TRIPLEDOTS
%token LPAREN RPAREN LBRACK RBRACK LBRACE RBRACE COLON
%token EOL EOF HASH TYPENAME TEMPLATE
%token NAMESPACE

%{
exception Bad_parse;;
open Errs;;
open Codemodel;;

%}

%start main /* the entry point */
%type <Codemodel.code> main
%%
main:
    atom_seq EOF                    { $1 }
;


atom_seq:
    /* empty  */                    { Codemodel.Sequence([]) }
|   atom_seq atom                   { Codemodel.Sequence( $1 :: $2 :: [] ) }
;

expr_atom_seq:
    /* empty */                     { Codemodel.Sequence([]) }
|   expr_atom_seq expr_atom         { Codemodel.Sequence( $1 :: $2 :: [] ) }
;
expr_atom_simple_seq:
    /* empty */                     				{ Codemodel.Sequence([]) }
|   expr_atom_simple expr_atom_simple_seq         { Codemodel.Sequence( $1 :: $2 :: [] ) }
;
atom:
    expr_atom                        { $1 }
|   SEMI                             { Codemodel.Token( ";" ) }
|   TYPE sp typedef SEMI             { Codemodel.Sequence(Codemodel.Token( $2 ) :: Codemodel.Type([], $3) :: []) }
|   TYPE sp error                    { disp_error ("typedef error, " ^ miss_semi); raise Bad_parse}
;

expr_atom_simple:
    TOKEN                           { Codemodel.Token( $1 ) }
|   TRIPLEDOTS                      { Codemodel.Token( "..." ) }
|   IDENT                           { Codemodel.Token( $1 ) }
|   AND                             { Codemodel.Token( "and" ) }
|   WITH                            { Codemodel.Token( "with" ) }
|   OF                              { Codemodel.Token( "of" ) }
|   AS                              { Codemodel.Token( "as" ) }
|   EQ                              { Codemodel.Token( "=" ) }
|   TYPENAME                        { Codemodel.Token( "typename" ) }
|   PRIVATE                         { Codemodel.Token( "private" ) }
|   PUBLIC                          { Codemodel.Token( "public" ) }
|   NAMESPACE                       { Codemodel.Token( "namespace" ) }
|   CONST                           { Codemodel.Token( "const" ) }
|   WHITESPACE                      { Codemodel.Whitespace( $1 ) }
|   SCOPE                           { Codemodel.Token( "::" ) }
|   STAR                            { Codemodel.Token( "*" ) }
|   COLON                           { Codemodel.Token( ":" ) }
|   AMP                             { Codemodel.Token( "&" ) }
|   LPAREN atom_seq RPAREN          { Codemodel.Sequence(Codemodel.Token("(") :: $2 :: Codemodel.Token(")") :: []) }
|	LPAREN error          			{ disp_error("unmatched left paren"); raise Bad_parse }
|   LBRACK atom_seq RBRACK          { Codemodel.Sequence(Codemodel.Token("[") :: $2 :: Codemodel.Token("]") :: []) }
|   LBRACK error                    { disp_error unmatched_lbk; raise Bad_parse }
;

expr_slightly_less_simple:
    GT                              { Codemodel.Token( ">" ) }
|   LT                              { Codemodel.Token( "<" ) }
|   COMMA                           { Codemodel.Token( "," ) }
|	expr_atom_simple 				{ $1 }
;
expr_atom:
	expr_slightly_less_simple		{ $1 }
|   NAMESPACE sp IDENT sp expr_slightly_less_simple_seq SEMI
									{ Codemodel.Token( "namespace" ^ $2 ^ $3 ^ $4 ^ Codemodel.code_to_cpp($5) ^ ";") }
|   NAMESPACE sp LBRACE atom_seq RBRACE
									{ Codemodel.Sequence(
											Codemodel.Token( "namespace" ^ $2 ^ "{" ) ::
											$4 ::
											Codemodel.Token( "}" ) ::
											[]
											)
									}
|   NAMESPACE sp IDENT sp expr_slightly_less_simple_seq LBRACE atom_seq RBRACE
									{ Codemodel.Grouping(
										Codemodel.ClassOrNamespaceScope($3),
										Codemodel.Sequence(
											Codemodel.Token( "namespace" ^ $2 ^ $3 ^ $4 ^ Codemodel.code_to_cpp($5)) ::
											Codemodel.Token( "{" ) ::
											$7 ::
											Codemodel.Token( "}" ) ::
											[]
											)
										)
									}
|   CLASS sp IDENT sp expr_slightly_less_simple_seq LBRACE atom_seq RBRACE
									{ Codemodel.Grouping(
										Codemodel.ClassOrNamespaceScope($3),
										Codemodel.Sequence(
											Codemodel.Token( "class" ^ $2 ^ $3 ^ $4 ^ Codemodel.code_to_cpp($5)) ::
											Codemodel.Token( "{" ) ::
											$7 ::
											Codemodel.Token( "}" ) ::
											[]
											)
										)
									}
|	CLASS sp IDENT sp expr_slightly_less_simple_seq SEMI
									{ Codemodel.Token( "class" ^ $2 ^ $3 ^ $4 ^ Codemodel.code_to_cpp($5) ^ ";") }
|   MATCH sp cpp_typename sp
		LPAREN sp atom_seq RPAREN sp
		match_body 					{ match $3 with s, w -> Codemodel.MatchExpression(s, Codemodel.Sequence(Codemodel.Token($2 ^ w ^ $4 ^ $6) :: $7 :: Codemodel.Token($9)::[]), $10) }
|   template_def                    { $1 }
|   LBRACE atom_seq RBRACE          { Codemodel.Sequence(Codemodel.Token("{") :: $2 :: Codemodel.Token("}") :: []) }
|   LBRACE atom_seq error           { disp_error unmatched_lbc; raise Bad_parse}
;

expr_atom_in_template_seq:
	/* empty */						{ Codemodel.Sequence([]) }
|	expr_atom_in_template_seq
		expr_atom_simple 			{ Codemodel.Sequence( $1 :: $2 :: [] ) }
;

expr_slightly_less_simple_seq:
	/* empty */ 					{ Codemodel.Sequence([]) }
|	expr_slightly_less_simple_seq
		expr_slightly_less_simple 	{ Codemodel.Sequence( $1 :: $2 :: [] ) }
;

template_def:
	TEMPLATE sp						{ Codemodel.Token("template" ^ $2) }
|	TEMPLATE sp LT sp template_args GT sp
		expr_atom
									{ Codemodel.Grouping(
										Codemodel.TemplateScope(match $5 with str, terms -> terms),
											Codemodel.Sequence(
												Codemodel.Token(
													"template  " ^ $2 ^ "<" ^ $4 ^ (match $5 with str, terms -> str) ^ ">" ^ $7
													) :: $8 :: []
												)
											)
									}
|	TEMPLATE sp LT sp template_args GT sp
		TYPE sp typedef SEMI sp
									{ Codemodel.Sequence(
										Codemodel.Token($2 ^ $4 ^ $7 ^ $9) :: Codemodel.Type((match $5 with str, terms -> terms), $10) :: Codemodel.Token(";" ^ $12) :: []) }
|	TEMPLATE sp LT sp template_args GT sp
		expr_slightly_less_simple_seq
		LBRACE error {disp_error ("Template error, " ^ unmatched_lbc); raise Bad_parse }

|   TEMPLATE sp LT sp template_args GT sp
		expr_slightly_less_simple_seq
        error {disp_error ("Template error, " ^ miss_semi); raise Bad_parse }
;
class_deriv_decl:
	/* empty */		{ "" }
|	COLON sp class_deriv_decl_2 { ":" ^ $2 ^ $3 }
|   COLON sp error {disp_error "miss super class name"; raise Bad_parse }
;

class_deriv_decl_2:
	PUBLIC sp cpp_typename  { "public " ^ $2  ^ match $3 with s,w -> s^w }
|	PRIVATE sp cpp_typename    { "private " ^ $2  ^ match $3 with s,w -> s^w }
|	cpp_typename   			{ match $1 with s,w -> s^w }
;

template_args:
	/* empty */ { ("", []) }
|	template_args_nonempty { $1 }
;
template_args_nonempty:
	template_term { match $1 with str,term -> (str, term :: []) }
|	template_args_nonempty COMMA sp template_term { match $1 with cur_str, cur_term -> match $4 with str, term -> (cur_str ^ "," ^ $3 ^ str, cur_term @ (term :: [])) }
|   template_args_nonempty error { disp_error ("Template args error, " ^ miss_com); raise Bad_parse }
;
template_term:
	CLASS sp IDENT sp opt_template_default { match $5 with str, deft -> ("class" ^ $2 ^ $3 ^ $4 ^ str, ("class", $3, deft)) }
|	CLASS sp TRIPLEDOTS sp IDENT sp opt_template_default { match $7 with str, deft -> ("class ... " ^ $2 ^ $4 ^ $5 ^ $6 ^ str, ("class ... ", $5, deft)) }
|	cpp_typename IDENT sp opt_template_default { (match $4 with str, deft -> match $1 with s,w -> s ^ w ^ $2 ^ $3 ^ str, (s, $2, deft)) }
|	cpp_typename sp TRIPLEDOTS sp IDENT sp opt_template_default { (match $7 with str, deft -> match $1 with s,w -> s ^ w ^ $2 ^ "..." ^ $4 ^ $5 ^ $6 ^ str, (s, $5, deft)) }
|   CLASS sp error {disp_error "miss class name"; raise Bad_parse }
|   cpp_typename error {disp_error "miss type name"; raise Bad_parse }
;

opt_template_default:
	/* empty */ { ("", Codemodel.NoTemplateDefault) }
|	template_default {$1};
;
template_default:
	EQ sp expr_atom_in_template_seq { ("=" ^ $2 ^ Codemodel.code_to_cpp($3), Codemodel.TemplateDefault(Codemodel.code_to_cpp($3))) }
;
sp:
    /* empty */               { "" }
|   WHITESPACE sp { $1 ^ $2 }
;

typedef:
    single_typedef                       { $1 :: [] }
|   single_typedef AND sp typedef        { match ($1, $4) with ((nm,w,b,bod),(nm2,w2,b2,bod2) :: tail) -> ((nm,w,b, bod) :: (nm2, $3 ^ w2, b2, bod2) :: tail) }
|   single_typedef error             	{ disp_error("invalid typedef. expected and "); raise Bad_parse }
;


typedef_body:
	/* empty */						  { Codemodel.Token("") }
|	LBRACE atom_seq RBRACE sp         { Codemodel.Sequence($2 :: Codemodel.Token($4) :: []) }
|   LBRACE error {disp_error ("typedef_body error, " ^ unmatched_lbc); raise Bad_parse }
;

single_typedef:
    IDENT sp EQ sp typebody typedef_body  { ($1, $2 ^ $4, (match $5 with t, ws -> t), Codemodel.Sequence(Codemodel.Token((match $5 with t, ws -> ws)) :: $6::[])) }
;

typebody:
    unnamed_typeterm                { (Codemodel.SimpleType(Codemodel.makeCPPTypes(match $1 with elts,wsp->elts)), match $1 with elts,wsp->wsp) } |
|   typetermlist common_body        { (Codemodel.Alternatives($1, match $2 with t,ws -> t), match $2 with t,ws->ws) }
;
common_body:
	/* empty */ 					{ (Codemodel.NoCommonBody, "") }
|	WITH sp unnamed_typeterm		{ (Codemodel.TupleCommonBody(Codemodel.makeCPPTypes(match $3 with elts, wsp -> elts)), "/*COMMONBODYWH*/" ^ $2 ^ (match $3 with elts, wsp -> wsp)) }
;
typetermlist:
    typeterm                                    { $1 :: [] }
|   typeterm MINUSPIPE sp typetermlist          { match $1 with Codemodel.NamedType(a,b,c,d,e) -> Codemodel.NamedType(a,b ^ $3,c,d,e) :: $4 }
|   MINUSPIPE sp typetermlist                   { match $3 with (Codemodel.NamedType(a,b,c,d,e))::tl ->
                                                Codemodel.NamedType(a,b^$2,c,d,e)::tl}
;


typeterm:
    typetermcore  { $1 }
|   typetermcore AS sp TOKEN sp  { match $1 with Codemodel.NamedType(a,b,c,d,e) -> Codemodel.NamedType(a,b,c,Codemodel.TypeOp($4),e ^ $3 ^ $5) }
;

typetermcore:
    IDENT sp OF sp unnamed_typeterm                           { Codemodel.NamedType($1, $2 ^ $4 ^ (match $5 with elts,wsp -> wsp), Codemodel.makeCPPTypes(match $5 with elts,wsp -> elts), Codemodel.NoTypeOp, "") }
|   IDENT sp OF sp LPAREN sp unnamed_typeterm RPAREN sp       { Codemodel.NamedType($1, $2 ^ $4 ^ $6 ^ (match $7 with elts,wsp -> wsp) ^ $9, Codemodel.makeCPPTypes(match $7 with elts,wsp -> elts), Codemodel.NoTypeOp, "") }
|   IDENT sp OF sp LPAREN sp RPAREN sp                        { Codemodel.NamedType($1, $2 ^ $4 ^ $6, Codemodel.makeCPPTypes([]), Codemodel.NoTypeOp, $8) }
|   IDENT sp OF sp LPAREN error {disp_error ("typedef error, " ^ unmatched_lp); raise Bad_parse }
  ;

unnamed_typeterm:
    individual_unnamed_typeterm								{ ((match $1 with e,w -> e) :: [], (match $1 with e,w->w)) }
|	individual_unnamed_typeterm COMMA sp unnamed_typeterm   { match $4 with (elts, whsp) -> ((match $1 with e,w -> e) :: elts, (match $1 with e,w->w) ^ $3 ^ whsp) }
;

individual_unnamed_typeterm:
    cpp_typename 	  	                        			 { match $1 with s,w -> ((s, Codemodel.Unnamed, "", Codemodel.NoMemo),w)  }
|   cpp_typename IDENT sp 		            		    	 { match $1 with s,w -> ((s, Codemodel.Named($2), "", Codemodel.NoMemo), w ^ $3)  }
|   cpp_typename IDENT sp EQ sp expr_atom_simple_seq	 	{ let code,whsp = Codemodel.extractWhitespace($6) in
																	match $1 with s,w -> ((s, Codemodel.Named($2), "", Codemodel.Memo("", code)), w ^ $3 ^ $5 ^ whsp)  }
|   cpp_typename IDENT sp EQ sp error 	{ disp_error("bad memo"); raise Bad_parse }
;

cpp_type_post_prename:
    cpp_type_post_prename_2 { $1 }
|	TRIPLEDOTS sp cpp_type_post_prename_2 { match $3 with s,w -> (" ... " ^ s, $2 ^ w) }
;

cpp_type_post_prename_2:
    IDENT sp                { ($1, $2) }
|   IDENT sp sharps         { match $3 with s,w -> ($1 ^ " " ^ s, $2 ^ w) }
;

cpp_type_single:
    cpp_type_post_prename { $1 }
|   TYPENAME sp cpp_type_post_prename { match $3 with s,w -> (" typename " ^ s, $2 ^ w) }
|   TEMPLATE sp cpp_type_post_prename { match $3 with s,w -> (" template " ^ s, $2 ^ w) }
;

namepart:
    SCOPE sp cpp_type_single { match $3 with s,w -> ("::" ^ " " ^ s, $2 ^ w) }
|   SCOPE error {disp_error ("not a valid member name(identifier)"); raise Bad_parse }
;
nameseq:
    /* empty */   { ("","") }
|   namepart nameseq                      { match $1 with s,w -> match $2 with s2, w2 -> (s ^ " " ^ s2, w ^ w2)  }
;

cpp_typename:
    cpp_typename_2  { $1 }
|   CONST sp cpp_typename_2 { match $3 with s,w -> ("const " ^ s, w ^ $2) }
;
cpp_typename_2:
    cpp_type_single sp nameseq cpp_type_post            {
                match $4 with post_s, post_w ->
                match $1 with ident_s, ident_w->
                match $3 with s, w ->
                    (ident_s ^ " " ^ s ^ " " ^ post_s, ident_w ^ $2 ^ w ^ post_w) }
;

cpp_type_post:
    /* empty */   { ("","") }
|   CONST sp cpp_type_post { match $3 with s,w->(" const " ^ s, $2 ^ w) }
|   STAR sp cpp_type_post { match $3 with s,w->(" * " ^ s, $2 ^ w) }
|   AMP sp cpp_type_post { match $3 with s,w->(" & " ^ s, $2 ^ w) }
|   error {disp_error "wrong type post"; raise Bad_parse }
;

sharps:
    LT sp sharpguts GT sp   { match $3 with s,w -> (" < " ^ s ^ " > ", $2 ^ w ^ $5) }
|   LT sp GT                { (" < > ", " ^ $2 ^ ") }
|   LT error {disp_error "unmatched < "; raise Bad_parse }
;
sharpguts:
    cpp_typename                            { match $1 with s, w -> (s,w) }
|   cpp_typename COMMA sp sharpguts         { match $1 with s,w -> match $4 with s2, w2 -> (s ^ " , " ^ s2, w ^ $3 ^ w2) }
;

match_body:
    MINUSPIPE sp match_term match_terms { (match $3 with (a,w,c) -> (a,$2^w,c)) :: $4 }
|   MINUSPIPE error {disp_error "match body error, may miss a ->> here"; raise Bad_parse }
|   error sp match_term match_terms {disp_error "match body error, may miss a -| here"; raise Bad_parse }
;
match_terms:
    /* empty */ { [] }
|   MINUSPIPE sp match_term match_terms { (match $3 with (a,w,c) -> (a,$2^w,c)) :: $4 }
|   MINUSPIPE error {disp_error "may miss a ->> here"; raise Bad_parse }
|   error {disp_error "-| expected"; raise Bad_parse }
;

match_pattern:
    match_pattern_term { $1 }
|   match_pattern_term COMMA sp match_pattern_multi_seq { Codemodel.TupleMatch($3, $1 :: $4) }
;
match_pattern_with:
	/* empty */ 										{ Codemodel.ThrowawayMatch("") }
|	WITH sp LPAREN sp match_pattern_multi_seq RPAREN sp 	{ Codemodel.TupleMatch($2 ^ $4 ^ $7, $5) }
;
match_pattern_term:
    IDENT sp LPAREN sp match_pattern_seq RPAREN sp match_pattern_with { Codemodel.TagMatch($1, $2 ^ $4, $5, $7, $8) }
|   LPAREN sp match_pattern_multi_seq RPAREN sp { Codemodel.TupleMatch($2 ^ $5, $3) }
|   IDENT sp { if $1 = "_" then Codemodel.ThrowawayMatch($2) else Codemodel.VariableMatch($1, $2) }
|   IDENT sp LPAREN sp match_pattern_seq error {disp_error ("pattern match error, " ^ unmatched_lp); raise Bad_parse }
|   LPAREN error {disp_error ("pattern match error, " ^ unmatched_lp); raise Bad_parse}
;

match_pattern_multi_seq:
     match_pattern_term { $1 :: [] }
|    match_pattern_term COMMA sp match_pattern_seq {
        (match $1 with
            Codemodel.TagMatch(a,b,c,d, e) -> Codemodel.TagMatch(a,b,c,d ^ $3, e)
        |   Codemodel.TupleMatch(a,b) -> Codemodel.TupleMatch(a ^ $3, b)            (* Really we should be more careful about where we put the whitespaces! *)
        |   Codemodel.ThrowawayMatch(w) -> Codemodel.ThrowawayMatch(w ^ $3)
        |   Codemodel.VariableMatch(v,w) -> Codemodel.VariableMatch(v,w ^ $3)
            ):: $4 }
;
match_pattern_seq:
    /* empty */ { [] }
|   match_pattern_multi_seq { $1 }
;

match_term:
    match_pattern MATCH_BECOMES sp LBRACE atom_seq RBRACE sp { ($1, $3 ^ $7, $5) }
;
ident_seq:
							{ ("", []) }
|	nonempty_ident_seq 		{ $1 }
;
nonempty_ident_seq:
	IDENT	sp	{ ($2, $1 :: []) }
|	IDENT sp COMMA sp nonempty_ident_seq	{ match $5 with w,l -> ($2 ^ $4 ^ w, $1 :: l) }
	;

