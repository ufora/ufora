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

import json
import numpy
import logging
import os
import os.path

class PerformanceObservationList(object):
    def __init__(self, seriesName, commit, mean, std, count):
        self.seriesName = seriesName
        self.commit = commit
        self.mean = mean
        self.std = std
        self.count = count

    @property
    def variance(self):
        return self.std * self.std

    def __add__(self, other):
        assert isinstance(other, PerformanceObservationList)

        if self.seriesName == other.seriesName:
            #we're adding multiple observations of the same thing across commits
            assert self.count is not None

            totalCount = (self.count + other.count)
            if totalCount == 0.0:
                totalCount = 1.0

            newMean = (self.mean * self.count + other.mean * other.count) / totalCount

            return PerformanceObservationList(
                self.seriesName,
                self.commit if self.commit == other.commit else None,
                newMean,
                ((self.variance * self.count + other.mean * other.variance +
                    ((self.mean - newMean) ** 2) * self.count +
                    ((other.mean - newMean) ** 2) * other.count
                    ) / totalCount) ** .5,
                self.count + other.count
                )
        else:
            #we're adding observations from different series, so this 'sum' is total time adding up
            return PerformanceObservationList(
                os.path.commonprefix([self.seriesName, other.seriesName]),
                self.commit if self.commit == other.commit else None,
                self.mean + other.mean,
                (self.variance + other.variance) ** .5,
                None
                )

    def __sub__(self, other):
        assert isinstance(other, PerformanceObservationList), type(other)

        #we're adding multiple observations of the same thing across commits
        assert self.count is not None
        assert self.seriesName == other.seriesName

        return PerformanceObservationList(
            self.seriesName,
            None,
            self.mean - other.mean,
            (self.variance + other.variance) ** .5,
            None
            )

    @staticmethod
    def sum(list):
        res = None

        for e in list:
            if res is None:
                res = e
            else:
                res = res + e

        return res

    @staticmethod
    def zscoreForDifference(above, below):
        """Calculate the statistics of the variable X-Y and return the zscore for it to not be zero"""
        if below.count < 2:
            return 0.0
        
        return (above.mean - below.mean) / below.std

    @staticmethod
    def createFromObservationList(seriesName, commit, obs):
        obs = [x for x in obs if x is not None]
        
        try:
            return PerformanceObservationList(seriesName, commit, numpy.mean(obs) if obs else 0.0, numpy.std(obs) if obs else 0.0, len(obs))
        except:
            logging.critical("obs: %s", obs)
            raise

class PerformanceTimeseries(object):
    def __init__(self, seriesName, commitIds, commitToObservationList):
        self.seriesName = seriesName
        self.commitIds = commitIds

        self.observations = {
            c: PerformanceObservationList.createFromObservationList(
                seriesName,
                c,
                commitToObservationList[c]
                ) if isinstance(commitToObservationList[c], list) else commitToObservationList[c]
            for c in commitIds if c in commitToObservationList
            }

    def performanceDegrades(self):
        for ix in range(1, len(self.commitIds)):
            above, below = self.splitIntoCommitSetsAtIndex(ix)

            if above is not None and below is not None:
                zScore = PerformanceObservationList.zscoreForDifference(above, below)

                if zScore > 4:
                    return True

        return False

    def performanceImproves(self):
        for ix in range(1, len(self.commitIds)):
            above, below = self.splitIntoCommitSetsAtIndex(ix)

            if above is not None and below is not None:
                zScore = PerformanceObservationList.zscoreForDifference(above, below)

                if zScore < -4:
                    logging.error("Commits %s, %s have means %s +- %s and %s += %s. diff is %s +- %s", self.commitIds[:ix], self.commitIds[ix:],
                        below.mean,
                        below.std,
                        above.mean,
                        above.std,
                        (above-below).mean,
                        (above-below).std
                        )
                    return True

        return False

    def splitIntoCommitSetsAtIndex(self, ix):
        below = PerformanceObservationList.sum(
            self.observations[c] for c in self.commitIds[:ix] if c in self.observations
            )
        above = PerformanceObservationList.sum(
            self.observations[c] for c in self.commitIds[ix:] if c in self.observations
            )

        return above, below



    def __add__(self, other):
        assert isinstance(other, PerformanceTimeseries)

        assert self.commitIds == other.commitIds

        obs = {}

        for c in self.commitIds:
            if c in self.observations:
                if c in other.observations:
                    obs[c] = self.observations[c] + other.observations[c]
                else:
                    obs[c] = self.observations[c]
            else:
                if c in other.observations:
                    obs[c] = other.observations[c]

        return PerformanceTimeseries(
            os.path.commonprefix([self.seriesName, other.seriesName]),
            self.commitIds,
            obs
            )

    def dataObservations(self):
        res = []

        for c in self.commitIds:
            if c in self.observations:
                res.append(self.observations[c].mean)
            else:
                res.append(None)

        return res

    def errorObservations(self):
        res = []

        for c in self.commitIds:
            if c in self.observations:
                obs = self.observations[c]
                res.append([obs.mean - obs.std * 2, obs.mean + obs.std * 2])
            else:
                res.append(None)

        return res


class PerformanceDataset(object):
    def __init__(self, dataBySeries, commitIds):
        """Create a PerformanceDataset using a dictionary of observations.

        dataBySeries should be a map

            seriesname -> commit -> list of observations


        commitIds should be a list of commitIds ordered by increasing time
        """
        self.dataBySeries = {
            seriesName: PerformanceTimeseries(seriesName, commitIds, dataBySeries[seriesName])
                for seriesName in dataBySeries
            }
        self.commitIds = commitIds

    def subseriesNames(self, prefix):
        return self.groupSeriesData(prefix).keys()

    def groupSeriesData(self, prefix):
        #first filter to the set we care about
        dataBySeries = {k: v for k,v in self.dataBySeries.iteritems() if k.startswith(prefix)}

        #get distinct groupings up to the dot in the name
        groups = set()

        for seriesName in dataBySeries:
            ix = seriesName.find('.', len(prefix) + 1)
            if ix > 0:
                groups.add(seriesName[:ix])
            else:
                groups.add(seriesName)

        groupDict = {g: {} for g in groups}

        for seriesName in dataBySeries:
            for g in groups:
                if seriesName.startswith(g):
                    groupDict[g][seriesName] = dataBySeries[seriesName]

        finalDataBySeries = {}

        for g in groups:
            for series in groupDict[g].values():
                if g not in finalDataBySeries:
                    finalDataBySeries[g] = series
                else:
                    finalDataBySeries[g] += series

        return finalDataBySeries

    def generateChartHtml(self, branchName, prefix, dataBySeries):
        seriesData = []
        for series in dataBySeries:
            dataSeq = []
            errSeq = []

            seriesData.append(
                {'name': series, 'data':
                    dataBySeries[series].dataObservations()
                    }
                )
            seriesData.append(
                {'name': series + " error", 'type': 'errorbar', 'data':
                    dataBySeries[series].errorObservations()}
                )

        return ("""
            <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
            <script src="//code.highcharts.com/highcharts.js"></script>
            <script src="//code.highcharts.com/highcharts-more.js"></script>
            <script src="//code.highcharts.com/modules/exporting.js"></script>

            <div id="container" style="height: 60%; width=100%; margin: auto; min-width: 310px"></div>

            <script type="text/javascript">
            $(function () {
                $('#container').highcharts({
                    chart: {
                        type: 'line'
                    },
                    title: {
                        text: 'Test Time'
                    },
                    xAxis: {
                        categories: [""" + ",".join('"%s"' % x for x in self.commitIds) + """]
                    },
                    yAxis: {
                        title: {
                            text: 'Time'
                        }
                    },
                    plotOptions: {
                        series: {
                            animation: false
                        }
                    },
                    series: """ + json.dumps(seriesData) + """
                });
            });
            </script>

            """)

