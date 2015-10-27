
(* <input ends with unterminated comment> *)
let unterm_cmt = "input ends with unterminated comment";;

(*<illegal newline in string constant "this is stri">*)
let newline_in_str = "illegal newline in string constant";;

(*<unterminated string constant "this is stri> "*)
let unterm_str1 = "unterminated string constant";;

(*unrecognized char: '@'*)
let unrecog_char1 = "unrecognized char";;

let miss_semi = "may miss a ';' here";;

let miss_com = "may miss a ',' here";;

let unmatched_lp = "unmatched ( ";;

let unmatched_lbc = "unmatched { ";;

let unmatched_lbk = "unmatched [ ";;

let wrong_pipe = "invalid use of -|";;

let wrong_match = "invalid use of ->>";;

let wrong_and = "invalid use of 'and' ";;

let end_line = ref 0;;
let h_file = ref "";;

let disp_error err =

	let start_pos = Parsing.symbol_start_pos() in
	let end_pos = Parsing.symbol_end_pos() in
    Printf.eprintf  "cppml: error in %s at line %d col %d: %s\n"
		!h_file
		(end_pos.Lexing.pos_lnum - !end_line + 1)
		(end_pos.Lexing.pos_cnum - end_pos.Lexing.pos_bol)
		err
