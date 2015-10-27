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

net = require 'net'
fs = require 'fs'
url = require 'url'
util = require 'util'
uuid = require 'node-uuid'
async = require 'async'
S = require 'string'
express = require 'express'
path = require 'path'

logger = null

#once populated, the searchIndex is a list of dictionaries, each of which
#looks like {category: ..., suggestedCompletion: ..., title: ..., content: ..., url: ...}
searchIndex = null
searchPageContent = null
MAX_RESULT_COUNT = 5000

module.exports.initialize = (app) ->
    logger = app.get 'logger'
    logger.info 'initializing kbSearch'

    readSearchIndexFromFile()

    kb = express()
    
    logger.info "Installing kbSearchRequestHandler"
    kb.get('/search.html', kbSearchRequestHandler)
    kb.get('/search.json', kbSearchRequestHandlerAsJson)

    pathToKbContent = path.join(__dirname, '..', 'generated_kb_files')

    kb.use('/', express.static(pathToKbContent))

    logger.info "Serving kb content: #{pathToKbContent}"

    app.use('/kb', kb)


readSearchIndexFromFile = () ->
    fs.readFile path.join(__dirname, "..", "generated_kb_files/searchIndex.json"), (err, content) ->
        try
            searchIndex = JSON.parse(content)
            logger.info("kbSearch loaded #{searchIndex.length} search entries")
        catch error
            logger.info("kbSearch failed to read json from #{content.length} bytes: #{error}")
    fs.readFile path.join(__dirname, "..", "generated_kb_files/index/search.html"), (err, content) ->
        searchPageContent = String(content)


kbSearchRequestHandler = (req, res) ->
    jsonEntries = searchKbFor(req.query.q, req.query.indexOffset, req.query.maxResults, req.query.orderCompletionsByDotDepth)

    if jsonEntries.responseType == 'error'
        res.redirect("/kb/index/page404.html")
        return

    res.send(
        searchPageContent.replace(
            '<gcse:searchresults-only></gcse:searchresults-only>',
            formatJsonSearchEntriesAsHtml(jsonEntries)
            )
        )



kbSearchRequestHandlerAsJson = (req, res) ->
    if not 'q' of req.query
        res.json
            responseType: 'error'
            reason: "request didn't contain a query parameter"
        return

    jsonEntries = searchKbFor(req.query.q, req.query.category, req.query.indexOffset, req.query.maxResults, req.query.orderCompletionsByDotDepth)

    res.json(jsonEntries)

searchKbFor = (query, category, indexOffset, maxResults, orderCompletionsByDotDepth) ->
    if not orderCompletionsByDotDepth?
        orderCompletionsByDotDepth = false

    if not query? or query.length <= 0
        return {responseType: 'error', reason: 'query string needs to be nonempty'}
    if not searchIndex?
        return {responseType: 'error', reason: 'the search index is empty'}

    if not maxResults?
        maxResults = 25
    else
        try
            maxResults = parseInt(maxResults)
        catch error
            return {responseType: 'error', reason: 'maxResults was not an integer'}
        if maxResults > MAX_RESULT_COUNT or maxResults < 1
            return {responseType: 'error', reason: 'maxResults was not an integer in [1,#{MAX_RESULT_COUNT}]'}

    if not indexOffset?
        indexOffset = 0
    else
        try
            indexOffset = parseInt(indexOffset)
        catch error
            return {responseType: 'error', reason: 'indexOffset was not an integer'}
        if indexOffset < 0
            return {responseType: 'error',reason: 'indexOffset was negative'}

    results = []

    for jsonEntry in searchIndex
        if matchesJsonEntry(query, category, jsonEntry)
            res = {}
            for name of jsonEntry
                if name != "content"
                    res[name] = jsonEntry[name]
            results.push res

    if orderCompletionsByDotDepth
        results = orderCompletionResultsByDotDepth(results)

    subslice = results[indexOffset..(indexOffset + maxResults)]

    return {
        responseType: 'success',
        results: subslice,
        totalResultCount: results.length
        }

orderCompletionResultsByDotDepth = (results) ->
    #if we match builtin.math and also builtin.math.linear, then
    #we want to filter out the second one because otherwise we dont
    #get useful completions bubbling to the top
    allFqes = {}
    for res in results
        if res.category == "fullyQualifiedName"
            allFqes[res.suggestedCompletion] = true

    results2 = []

    for res in results
        results2.push(res)

    dotDepth = (name) ->
        depth = 0
        while allFqes[popLastDottedElementOf(name)]?
            newName = popLastDottedElementOf(name)
            if newName == name
                return depth
            else
                name = newName
            depth += 1
        return depth

    results2.sort (a,b) ->
        if a.category < b.category
            return -1
        if a.category > b.category
            return 1
        if a.category != "fullyQualifiedName"
            return 0

        depthDiff = dotDepth(a.suggestedCompletion) - dotDepth(b.suggestedCompletion)

        if depthDiff < 0
            return -1
        if depthDiff > 0
            return 1
        return 0

    return results2


popLastDottedElementOf = (fullyQualifiedName)->
    ix = fullyQualifiedName.lastIndexOf(".")
    if ix == -1
        return fullyQualifiedName

    return fullyQualifiedName[0..(ix-1)]

matchesJsonEntry = (query, category, jsonEntry) ->
    if category? and jsonEntry.category != category
        return false
    return jsonEntry.content.toUpperCase().indexOf(query.toUpperCase()) > -1

formatJsonSearchEntriesAsHtml = (jsonEntries) ->
    buffer = ""

    if jsonEntries.results.length == 0
        buffer = "Sorry, no search results matched your query"
    else
        for entry in jsonEntries.results
            if entry.category == "fullyQualifiedName"
                buffer += "#{entry.objectKind} <a href='#{entry.url}'>#{entry.suggestedCompletion}</a><br>"
            if entry.category == "builtinSourceCode"
                buffer += "Source code file <a href='#{entry.url}'><strong>#{entry.filename}</strong>:#{entry.lineNumber}</a><br>"

    return buffer


