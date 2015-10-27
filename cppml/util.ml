let
	strip_whitespace str = (
		if str = "" then "" else
		let search_pos init p next =
		let rec search i =
		  if p i then raise(Failure "empty") else
		  match str.[i] with
		  | ' ' | '\n' | '\r' | '\t' -> search (next i)
		  | _ -> i
		in
		search init   in   let len = String.length str in   try
		let left = search_pos 0 (fun i -> i >= len) (succ)
		and right = search_pos (len - 1) (fun i -> i < 0) (pred)
		in
		String.sub str left (right - left + 1)   with   | Failure "empty" -> ""
		)
	;;
let
	file_contents filename =
		let lines = ref [] in
		let chan = open_in filename in
		try
			while true; do
				lines := input_line chan :: !lines
			done;""
		with End_of_file ->
			close_in chan;
			(String.concat "\n" (List.rev !lines))
	;;
let
	relativePath pathname =
		let cppmlPath = Sys.argv.(0) in
		(* hack out the last five characters *)
		(String.sub cppmlPath 0 (String.length cppmlPath - 5)) ^ pathname
	;;