{
open Parser
open Errs
exception Eof
exception Ex

}
rule
	token = parse
    ("\n# " ((['0' - '9']+) as line_no) " " (('"' [^ '"']* '"') as s) (([^ '\n']* ) )) as z
			{
			Lexing.new_line(lexbuf);
             if String.length(s) > 5 && (String.sub s (String.length(s) - 5) 4) = "ppml" then
				 let _ = end_line := (lexbuf.Lexing.lex_curr_p).Lexing.pos_lnum - int_of_string(line_no) + 2 in
                 let _ = h_file := s in
              WHITESPACE(z)
			else
				WHITESPACE(z ^ (String.concat "" ((until_preprocml lexbuf)) ))
			}
  | ("# " ((['0' - '9']+) as line_no) " " (('"' [^ '"']* '"') as s) (([^ '\n']* ) )) as z
			{
			if String.length(s) > 5 && (String.sub s (String.length(s) - 5) 4) = "ppml" then
				 let _ = end_line := (lexbuf.Lexing.lex_curr_p).Lexing.pos_lnum - int_of_string(line_no) + 2 in
                 let _ = h_file := s in
				WHITESPACE(z)
			else
				WHITESPACE(z ^ (String.concat "" ((until_preprocml lexbuf)) ))
			  }
  | "\n" { Lexing.new_line(lexbuf); WHITESPACE("\n") }
  | [' ' '\t']+ as s     { WHITESPACE(s) }
  | "@type" { TYPE }
  | "@match" { MATCH }
  | "typename" { TYPENAME }
  | "public" { PUBLIC }
  | "private" { PRIVATE }
  | "namespace" { NAMESPACE }
  | "template" { TEMPLATE }
  | "class" { CLASS }
  | "const" { CONST }
  | "with" { WITH }
  |	"and" 		   { AND }
  |	"as" 		   { AS }
  |	"of" 		   { OF }

  | "/*" as s { WHITESPACE(s ^ comment lexbuf) }
  | "//" ([^ '\n'])* "\n"  as s  { Lexing.new_line(lexbuf); WHITESPACE(s) }
  | ('#' [^ '\n']* "\n") as s        { Lexing.new_line(lexbuf);
                                    WHITESPACE(s) }
  | ('#' [^ '\n']*) as s     		   {  WHITESPACE(s) }

  | '"' ([^ '"' '\\'] | ('\\' _))* '"'  as s { TOKEN(s) }
  | '\'' ([^ '\''] | "\\\'")* '\''  as s { TOKEN(s) }
  | (['a'-'z' 'A'-'Z' '_']+ ['A'-'Z' 'a'-'z' '0'-'9' '_' ]*) as s { IDENT(s) }
  | ('-')? ['0'-'9']+ as s { TOKEN(s) }

  | "->>"       { MATCH_BECOMES }
  | "-|"        { MINUSPIPE }

  | ("<<=" | ">>=" | "++=" | "--=" | "&&=" | "||=") as s       { TOKEN(s) }
  | ("!=" | "<=" | "==" | ">=" | "+=" | "-=" | "&=" | "|=" | "/=" | "*=" | "%=" | "^=" ) as s       { TOKEN(s) }
  | ("<<" | ">>" | "++" | "--" | "&&" | "||") as s       { TOKEN(s) }


  | "..."       { TRIPLEDOTS }
  | "::"        { SCOPE }
  |	"=" 		   { EQ }
  |	"*" 		   { STAR }
  |	"&" 		   { AMP }


  | ("<")        { LT }
  | (">")        { GT }
  | ("!" | "~" | "\\" | "|" | "." | "*" | "/" | "-" | "+" | "^" | "&" | "%" | "?" | "???????") as s       { TOKEN(s) }

  | ':'            { COLON }
  | ','            { COMMA }
  | ';'            { SEMI }
  | '('            { LPAREN }
  | ')'            { RPAREN }
  | '{'            { LBRACE }
  | '}'            { RBRACE }
  | '['            { LBRACK }
  | ']'            { RBRACK }
  | eof            { EOF }
  | _             {disp_error (unrecog_char1); raise Ex} (* '$' symbols, etc *)
and
	comment = parse
		"*/" as s { s }
	|	_ [^ '*' '/' '\n']* as s { s ^ comment lexbuf }
	|	'\n' { Lexing.new_line(lexbuf); "\n" ^ comment lexbuf }
	|	eof { disp_error (unterm_cmt);raise End_of_file (*print_string("reached end of file in comment!\n"); raise End_of_file*)}
and
	until_preprocml = parse
    ("\n# " ((['0' - '9']+) as line_no) ' ' (('"' [^ '"']* '"') as s) (([^ '\n']* ) )) as z
			{
             Lexing.new_line (lexbuf);
             if String.length(s) > 5 && (String.sub s (String.length(s) - 5) 4) = "ppml" then
				 let _ = end_line := (lexbuf.Lexing.lex_curr_p).Lexing.pos_lnum - int_of_string(line_no) + 2 in
                 let _ = h_file := s in
                 z :: []
			 else
				z :: until_preprocml lexbuf
			   }
    | ("# " ((['0' - '9']+) as line_no) ' ' (('"' [^ '"']* '"') as s) (([^ '\n']* ) )) as z
			{
             if String.length(s) > 5 && (String.sub s (String.length(s) - 5) 4) = "ppml" then
				 let _ = end_line := (lexbuf.Lexing.lex_curr_p).Lexing.pos_lnum - int_of_string(line_no) + 2 in
                 let _ = h_file := s in
                 z :: []
			 else
				z :: until_preprocml lexbuf
		   }
	| ("\n" [^ '\n']* )  as s
           { Lexing.new_line (lexbuf);
             s :: until_preprocml lexbuf }
	| eof { [] }
