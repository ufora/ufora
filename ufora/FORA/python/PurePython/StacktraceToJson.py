import ufora.native.FORA as ForaNative

def implvalStacktraceToJson(stacktrace):
    assert isinstance(stacktrace, ForaNative.ImplValContainer), stacktrace
    if not stacktrace.isStackTrace():
        stacktrace = stacktrace[0]

    codeLocations = stacktrace.getStackTrace()

    if codeLocations is None:
        return None

    def formatCodeLocation(c):
        if not c.defPoint.isExternal():
            return None
        def posToJson(simpleParsePosition):
            return {
                'line': simpleParsePosition.line,
                'col': simpleParsePosition.col
                }
        return {
            'path': list(c.defPoint.asExternal.paths),
            'range': {
                'start': posToJson(c.range.start),
                'stop': posToJson(c.range.stop)
                }
            }

    return tuple(
            x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None
            )


    
