set print thread-events off
handle SIGPIPE nostop pass
run
thread apply all bt
generate-core-file
