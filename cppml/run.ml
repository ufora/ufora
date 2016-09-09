open Parser;;
open Lexer;;

let arg = Sys.argv.(1) ;;

let args = Array.to_list(Sys.argv);;
let wantsTrace = List.exists (function x->x="-t") args;;
Parsing.set_trace wantsTrace;;


let code = Parser.main Lexer.token (Lexing.from_channel (if arg = "-" then stdin else open_in arg))  in
print_string(Codemodel.code_to_cpp_whole_file(code))

;;
