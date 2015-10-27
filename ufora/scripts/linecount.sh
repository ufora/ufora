#/usr/bin/sh

find ufora | grep '\([h|c]pp\|py\)' | grep -v '/.build/' | grep -v '\(png\|pyc\|\.waf\|java_opengl\)' | grep -v ttf | xargs wc
