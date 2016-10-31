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

import unittest

import ufora.FORA.python.FORA as FORA

class TestGradientBoosting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FORA.initialize()

    def test_gradientBoostedBinaryClassificationExhaustiveSplits(self):
        with open("hastie-X.csv") as f:
            text = "parsing.csv('''%s''', defaultColumnType: Float64)" % f.read()
            X = FORA.eval(text)
        with open("hastie-y.csv") as f:
            y = FORA.eval("parsing.csv('''%s''', defaultColumnType: Float64)" % f.read())


        res = FORA.eval("""
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedClassifierBuilder(
                    splitMethod: `exhaustive, nBoosts: 10, maxDepth: 4
                    )

            let fit = builder.fit(X, y);
            assertions.assertEqual(fit.score(X, y), 1.0)
            """, { 'X' : X, 'y' : y })

        self.assertTrue(res)

    def test_regressionTrees_1(self):
        res = FORA.eval(
            """    
            let regressionTree = 
                math.tree.RegressionTree.buildTree(
                    df, yDim: 2, maxDepth: 5, minSamplesSplit: 50
                    );

            let expectedValues = 
                [-0.953882430908236, 99.7799382797797, -0.953882430908236, 
                 -0.953882430908236, -1.85651176009063, -1.85651176009063,  
                 -0.731458273696544, -0.953882430908236, -0.731458273696544, 
                 -0.731458273696544];

            let computedValues = 
                Vector.range(size(expectedValues)) ~~ { 
                    regressionTree.predict(df("X", "Y")[_])
                    };

            assertions.assertAllClose(expectedValues, computedValues);

            computedValues = 
                Vector.range(size(expectedValues)) ~~ { 
                    regressionTree.predict(df[_])
                    };

            assertions.assertAllClose(expectedValues, computedValues);

            let predictedValues = regressionTree.predict(df);
            let meanSquareError = 
                math.stats.mean((predictedValues - df.getColumn("Z")) ** 2);

            assertions.assertClose(meanSquareError, 0.986815325486888)""",
            { 'df' : self.generateDataset(1000, 42) }
            )

        self.assertTrue(res)

    def test_regressionTrees_2(self):
        res = FORA.eval(
            """
            let X = df("X", "Y");
            let y = df("Z");

            let regressionTreeBuilder = 
                math.tree.RegressionTree.RegressionTreeBuilder(
                    maxDepth: 5, minSamplesSplit: 50
                    );

            let regressionTree = regressionTreeBuilder.fit(X, y);

            assertions.assertClose(regressionTree.predict(df[0]), -0.953882430908236);
            """,
            { 'df' : self.generateDataset(1000, 42) }
            )

        self.assertTrue(res)

    def test_regressionTrees_3(self):
        res = FORA.eval(
            """
            let regressionTree = 
                math.tree.RegressionTree.buildTree(
                    df, yDim: 2, maxDepth: 5, minSamplesSplit: 50,
                    splitMethod: `exhaustive
                    );

            let predictedValues = regressionTree.predict(df);
 
            let meanSquareError = 
                math.stats.mean((predictedValues - df.getColumn("Z")) ** 2)

            assertions.assertClose(meanSquareError, 0.986815325486888)
            """,
            { 'df' : self.generateDataset(1000, 42) }
            )

        self.assertTrue(res)

    def test_regresionTrees_4(self):
        res = FORA.eval(
            """
            let treeBuilder1 = 
                math.tree.RegressionTree.RegressionTreeBuilder(
                    maxDepth:2, minSamplesSplit:2,
                    splitMethod:`exhaustive
                    );
            let treeBuilder2 = 
                math.tree.RegressionTree.RegressionTreeBuilder(
                    maxDepth:5, minSamplesSplit:2,
                    splitMethod:`exhaustive
                    );

            let tree1 = treeBuilder1.fit(X, y);

            let tree2 = treeBuilder2.fit(X, y);
            
            let mse1 = ((tree1.predict(X) - y.getColumn("y")) ** 2).sum() / size(X);
            
            let mse2 = ((tree2.predict(X) - y.getColumn("y")) ** 2).sum() / size(X);

            assertions.assertClose(mse1, 0.12967126328231796)
            assertions.assertClose(mse2, 0.025236948989861896)
            """,
            { 'X' : self.X(), 'y' : self.y() }
            )

        self.assertTrue(res)

    def test_regressionTrees_5(self):
        res = FORA.eval(
            """
            let y_median = math.stats.median(y.getColumn(0));
            let y_medians = dataframe.Series(Vector.uniform(size(X), y_median));
            
            let neg_gradient = (y.getColumn(0) - y_medians) ~~ math.sign;
            neg_gradient = dataframe.DataFrame([neg_gradient])

            let treeBuilder = 
                math.tree.RegressionTree.RegressionTreeBuilder(
                    maxDepth:2, minSamplesSplit:2,
                    splitMethod:`exhaustive
                    );
            let tree = treeBuilder.fit(X, neg_gradient)
            
            // checked against scikit
            assertions.assertClose(tree.score(X, y), 0.53214422106820458)
            """,
            { 'X' : self.X(), 'y' : self.y() }
            )

        self.assertTrue(res)

    def test_gradientBoostedRegression_1(self):
        # checked against python
        score = FORA.eval(
            """
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedRegressorBuilder(
                    splitMethod:`exhaustive, nBoosts: 10
                    );

            let fit = builder.fit(X,y);
            fit.score(X, y)""",
            { 'X' : self.X(), 'y' : self.y() }
            )

        self.assertAlmostEqual(score, 0.99481448138431761)

    def test_gradientBoostedRegressionWithLearningRate_l2_loss(self):
        score = FORA.eval(
            """
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedRegressorBuilder(
                    splitMethod: `exhaustive, nBoosts: 100, learningRate: 0.01,
                    maxDepth: 3, minSamplesSplit: 2
                    );

            let fit = builder.fit(X,y);
            fit.score(X, y)""",
            { 'X' : self.X(), 'y' : self.y() }
            )

        # scikit gives 0.72390015177854738 here, which is close enough
        self.assertAlmostEqual(score, 0.7290072585890333)

    def test_gradientBoostedRegressionWithLearningRate_lad_loss(self):
        score = FORA.eval(
            """
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedRegressorBuilder(
                    loss:`lad,
                    splitMethod:`exhaustive, nBoosts: 100, learningRate: 0.01,
                    maxDepth: 2, minSamplesSplit: 2
                    );

            let fit = builder.fit(X,y);
            fit.score(X, y)""",
            { 'X' : self.X(), 'y' : self.y() }
            )

        # scikit gives 0.62389191111166742 here
        self.assertAlmostEqual(score, 0.6647719923783376)

    def test_gradientBoostedRegressionAbsoluteLoss(self):
        score = FORA.eval(
            """
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedRegressorBuilder(
                splitMethod:`exhaustive, nBoosts: 1, loss: `lad, maxDepth: 2
                );

            let fit = builder.fit(X,y);
            fit.score(X, y)""",
            { 'X' : self.X(), 'y' : self.y() }
            )

        # python gives a slightly different answer here: 0.7147891405349398
        # however, for gradient boosting, they use a different split criteria 
        # instead of the most basic mean square error: they use a modification 
        # due to Friedman which can be found in his original paper on Boosting,
        # or in the scikit source.

        self.assertAlmostEqual(score, 0.716655282631498)

    def test_gradientBoostedClassificationExhaustiveSplits_1(self):
        score = FORA.eval("""
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedClassifierBuilder(
                    splitMethod:`exhaustive, nBoosts: 10, maxDepth: 1
                );

            let fit = builder.fit(X, y);
            fit.score(X, y)""", 
            {'X': self.irisX(), 'y': self.irisY()})

        self.assertAlmostEqual(score, 0.83999999999999997)

    def test_gradientBoostedClassificationSamplingSplits_1(self):
        score = FORA.eval("""
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedClassifierBuilder(
                    splitMethod:`sample, nBoosts: 1, maxDepth: 1
                );

            let fit = builder.fit(X, y);

            // this answer diverges a bit from scikit, and I'm not exactly sure
            // why. however, as noted in the regression tests, we're not 
            // using exactly the same splitting criteron as scikit
            fit.score(X, y)""", 
            {'X': self.irisX(), 'y': self.irisY()})

        self.assertAlmostEqual(score, 0.7466666666666667)

    def test_gradientBoostedClassificationSamplingSplits_2(self):
        score = FORA.eval("""
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedClassifierBuilder(
                    splitMethod:`sample, nBoosts: 100, maxDepth:1
                );

            let fit = builder.fit(X, y);

            // this answer diverges a bit from scikit, and I'm not exactly sure
            // why. however, as noted in the regression tests, we're not 
            // using exactly the same splitting criteron as scikit
            fit.score(X, y)""", 
            {'X': self.irisX(), 'y': self.irisY()})

        self.assertAlmostEqual(score, 0.8733333333333333)

    def test_gradientBoostedClassificationWithLearningRate(self):
        score = FORA.eval("""
            let builder = 
                math.ensemble.gradientBoosting.GradientBoostedClassifierBuilder(
                    splitMethod:`sample, nBoosts: 100, maxDepth: 1, 
                    learningRate: 0.1
                );

            let fit = builder.fit(X, y);

            fit.score(X, y)""", 
            {'X': self.irisX(), 'y': self.irisY()})

        self.assertAlmostEqual(score, 0.84)

    def X(self):
        xData = FORA.eval('''
        """
        5.71874087e-04,
        9.14413867e-02,
        9.68347894e-02,
        1.36937966e-01,
        1.95273916e-01,
        2.49767295e-01,
        2.66812726e-01,
        4.25221057e-01,
        4.61692974e-01,
        4.91734169e-01,
        5.11672144e-01,
        5.16130033e-01,
        6.50142861e-01,
        6.87373521e-01,
        6.96381736e-01,
        7.01934693e-01,
        7.33642875e-01,
        7.33779454e-01,
        8.26770986e-01,
        8.49152098e-01,
        9.31301057e-01,
        9.90507445e-01,
        1.02226125e+00,
        1.05814058e+00,
        1.32773330e+00,
        1.40221996e+00,
        1.43887669e+00,
        1.46807074e+00,
        1.51166286e+00,
        1.56712089e+00,
        1.57757816e+00,
        1.72780364e+00,
        1.73882930e+00,
        1.98383737e+00,
        1.98838418e+00,
        2.07027994e+00,
        2.07089635e+00,
        2.08511002e+00,
        2.08652401e+00,
        2.09597257e+00,
        2.10553813e+00,
        2.23946763e+00,
        2.45786580e+00,
        2.57444556e+00,
        2.66582642e+00,
        2.67948203e+00,
        2.69408367e+00,
        2.79344914e+00,
        2.87058803e+00,
        2.93277520e+00,
        2.94652768e+00,
        3.31897323e+00,
        3.35233755e+00,
        3.39417766e+00,
        3.42609750e+00,
        3.43250464e+00,
        3.45938557e+00,
        3.46161308e+00,
        3.47200079e+00,
        3.49879180e+00,
        3.60162247e+00,
        3.62998993e+00,
        3.74082827e+00,
        3.75072157e+00,
        3.75406052e+00,
        3.94639664e+00,
        4.00372284e+00,
        4.03695644e+00,
        4.17312836e+00,
        4.38194576e+00,
        4.39058718e+00,
        4.39071252e+00,
        4.47303332e+00,
        4.51700958e+00,
        4.54297752e+00,
        4.63754290e+00,
        4.72297378e+00,
        4.78944765e+00,
        4.84130788e+00,
        4.94430544e+00""".split(",").apply(Float64);''')

        return FORA.eval(
            "dataframe.DataFrame([xData], columnNames:['X'])", 
            { 'xData' : xData }
            )

    def y(self):
        yData = FORA.eval('''
        """-1.1493464 ,  0.09131401,  0.09668352,  0.13651039,  0.19403525,
        -0.12383814,  0.26365828,  0.41252216,  0.44546446,  0.47215529,
        -0.26319138,  0.49351799,  0.60530013,  0.63450933,  0.64144608,
        1.09900119,  0.66957978,  0.66968122,  0.73574834,  0.75072053,
        1.4926134 ,  0.8363043 ,  0.8532893 ,  0.87144496,  0.97060533,
        -0.20183403,  0.99131122,  0.99472837,  0.99825213,  0.99999325,
        1.21570343,  0.98769965,  0.98591565,  0.9159044 ,  0.91406986,
        -0.51669013,  0.8775346 ,  0.87063055,  0.86993408,  0.86523559,
        0.37007575,  0.78464608,  0.63168655,  0.53722799,  0.45801971,
        0.08075119,  0.43272116,  0.34115328,  0.26769953,  0.20730318,
        1.34959235, -0.17645185, -0.20918837, -0.24990778, -0.28068224,
        -1.63529379, -0.31247075, -0.31458595, -0.32442911, -0.34965155,
        -0.29371122, -0.46921115, -0.56401144, -0.57215326, -0.57488849,
        -0.95586361, -0.75923066, -0.78043659, -0.85808859, -0.94589863,
        -0.6730775 , -0.94870673, -0.97149093, -0.98097408, -0.98568417,
        -0.20828128, -0.99994398, -0.99703245, -0.99170146, -0.9732277"""
            .split(",").apply(Float64);''')

        return FORA.eval(
            "dataframe.DataFrame([yData], columnNames: ['y'])",
            { 'yData' : yData }
            )        

    def irisY(self):
        dataStr = """0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     0,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     1,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                     2,
                    2"""

        tr = FORA.eval("math.Matrix('''%s'''.split(',').apply(Float64), (150, 1), `row)" % dataStr)

        return self.dataFrameFromMatrix(tr)

    def irisX(self):
        dataStr = """5.1,3.5,1.4,0.2,
                     4.9,3.0,1.4,0.2,
                     4.7,3.2,1.3,0.2,
                     4.6,3.1,1.5,0.2,
                     5.0,3.6,1.4,0.2,
                     5.4,3.9,1.7,0.4,
                     4.6,3.4,1.4,0.3,
                     5.0,3.4,1.5,0.2,
                     4.4,2.9,1.4,0.2,
                     4.9,3.1,1.5,0.1,
                     5.4,3.7,1.5,0.2,
                     4.8,3.4,1.6,0.2,
                     4.8,3.0,1.4,0.1,
                     4.3,3.0,1.1,0.1,
                     5.8,4.0,1.2,0.2,
                     5.7,4.4,1.5,0.4,
                     5.4,3.9,1.3,0.4,
                     5.1,3.5,1.4,0.3,
                     5.7,3.8,1.7,0.3,
                     5.1,3.8,1.5,0.3,
                     5.4,3.4,1.7,0.2,
                     5.1,3.7,1.5,0.4,
                     4.6,3.6,1.0,0.2,
                     5.1,3.3,1.7,0.5,
                     4.8,3.4,1.9,0.2,
                     5.0,3.0,1.6,0.2,
                     5.0,3.4,1.6,0.4,
                     5.2,3.5,1.5,0.2,
                     5.2,3.4,1.4,0.2,
                     4.7,3.2,1.6,0.2,
                     4.8,3.1,1.6,0.2,
                     5.4,3.4,1.5,0.4,
                     5.2,4.1,1.5,0.1,
                     5.5,4.2,1.4,0.2,
                     4.9,3.1,1.5,0.1,
                     5.0,3.2,1.2,0.2,
                     5.5,3.5,1.3,0.2,
                     4.9,3.1,1.5,0.1,
                     4.4,3.0,1.3,0.2,
                     5.1,3.4,1.5,0.2,
                     5.0,3.5,1.3,0.3,
                     4.5,2.3,1.3,0.3,
                     4.4,3.2,1.3,0.2,
                     5.0,3.5,1.6,0.6,
                     5.1,3.8,1.9,0.4,
                     4.8,3.0,1.4,0.3,
                     5.1,3.8,1.6,0.2,
                     4.6,3.2,1.4,0.2,
                     5.3,3.7,1.5,0.2,
                     5.0,3.3,1.4,0.2,
                     7.0,3.2,4.7,1.4,
                     6.4,3.2,4.5,1.5,
                     6.9,3.1,4.9,1.5,
                     5.5,2.3,4.0,1.3,
                     6.5,2.8,4.6,1.5,
                     5.7,2.8,4.5,1.3,
                     6.3,3.3,4.7,1.6,
                     4.9,2.4,3.3,1.0,
                     6.6,2.9,4.6,1.3,
                     5.2,2.7,3.9,1.4,
                     5.0,2.0,3.5,1.0,
                     5.9,3.0,4.2,1.5,
                     6.0,2.2,4.0,1.0,
                     6.1,2.9,4.7,1.4,
                     5.6,2.9,3.6,1.3,
                     6.7,3.1,4.4,1.4,
                     5.6,3.0,4.5,1.5,
                     5.8,2.7,4.1,1.0,
                     6.2,2.2,4.5,1.5,
                     5.6,2.5,3.9,1.1,
                     5.9,3.2,4.8,1.8,
                     6.1,2.8,4.0,1.3,
                     6.3,2.5,4.9,1.5,
                     6.1,2.8,4.7,1.2,
                     6.4,2.9,4.3,1.3,
                     6.6,3.0,4.4,1.4,
                     6.8,2.8,4.8,1.4,
                     6.7,3.0,5.0,1.7,
                     6.0,2.9,4.5,1.5,
                     5.7,2.6,3.5,1.0,
                     5.5,2.4,3.8,1.1,
                     5.5,2.4,3.7,1.0,
                     5.8,2.7,3.9,1.2,
                     6.0,2.7,5.1,1.6,
                     5.4,3.0,4.5,1.5,
                     6.0,3.4,4.5,1.6,
                     6.7,3.1,4.7,1.5,
                     6.3,2.3,4.4,1.3,
                     5.6,3.0,4.1,1.3,
                     5.5,2.5,4.0,1.3,
                     5.5,2.6,4.4,1.2,
                     6.1,3.0,4.6,1.4,
                     5.8,2.6,4.0,1.2,
                     5.0,2.3,3.3,1.0,
                     5.6,2.7,4.2,1.3,
                     5.7,3.0,4.2,1.2,
                     5.7,2.9,4.2,1.3,
                     6.2,2.9,4.3,1.3,
                     5.1,2.5,3.0,1.1,
                     5.7,2.8,4.1,1.3,
                     6.3,3.3,6.0,2.5,
                     5.8,2.7,5.1,1.9,
                     7.1,3.0,5.9,2.1,
                     6.3,2.9,5.6,1.8,
                     6.5,3.0,5.8,2.2,
                     7.6,3.0,6.6,2.1,
                     4.9,2.5,4.5,1.7,
                     7.3,2.9,6.3,1.8,
                     6.7,2.5,5.8,1.8,
                     7.2,3.6,6.1,2.5,
                     6.5,3.2,5.1,2.0,
                     6.4,2.7,5.3,1.9,
                     6.8,3.0,5.5,2.1,
                     5.7,2.5,5.0,2.0,
                     5.8,2.8,5.1,2.4,
                     6.4,3.2,5.3,2.3,
                     6.5,3.0,5.5,1.8,
                     7.7,3.8,6.7,2.2,
                     7.7,2.6,6.9,2.3,
                     6.0,2.2,5.0,1.5,
                     6.9,3.2,5.7,2.3,
                     5.6,2.8,4.9,2.0,
                     7.7,2.8,6.7,2.0,
                     6.3,2.7,4.9,1.8,
                     6.7,3.3,5.7,2.1,
                     7.2,3.2,6.0,1.8,
                     6.2,2.8,4.8,1.8,
                     6.1,3.0,4.9,1.8,
                     6.4,2.8,5.6,2.1,
                     7.2,3.0,5.8,1.6,
                     7.4,2.8,6.1,1.9,
                     7.9,3.8,6.4,2.0,
                     6.4,2.8,5.6,2.2,
                     6.3,2.8,5.1,1.5,
                     6.1,2.6,5.6,1.4,
                     7.7,3.0,6.1,2.3,
                     6.3,3.4,5.6,2.4,
                     6.4,3.1,5.5,1.8,
                     6.0,3.0,4.8,1.8,
                     6.9,3.1,5.4,2.1,
                     6.7,3.1,5.6,2.4,
                     6.9,3.1,5.1,2.3,
                     5.8,2.7,5.1,1.9,
                     6.8,3.2,5.9,2.3,
                     6.7,3.3,5.7,2.5,
                     6.7,3.0,5.2,2.3,
                     6.3,2.5,5.0,1.9,
                     6.5,3.0,5.2,2.0,
                     6.2,3.4,5.4,2.3,
                    5.9,3.0,5.1,1.8"""
        
        X = FORA.eval(
            "math.Matrix('''%s'''.split(',').apply(Float64), (150, 4), `row)" % 
            dataStr
            )

        X = self.dataFrameFromMatrix(X)
        return FORA.eval("dataframe.DataFrame(X.columns[,2])", { 'X': X })

    def generateDataset(self, count, seed):
        return FORA.eval(
            """
            fun(count, seed) {
                let impulse = fun(x, y) {
                    if (x > 0 and y > 0)
                        return 100.0;
                    if (x <= 0)
                        return -1
                    return -2
                    };

                let normal = iterator(math.random.Normal(0.0, 1.0, seed));
                let x0 = [];
                let x1 = [];
                let y = [];
                for _ in sequence(count) 
                    {
                    let x0_val = pull normal;
                    let x1_val = pull normal;
                    let y_val = (pull normal) + impulse(x0_val, x1_val)

                    x0 = x0 :: x0_val;
                    x1 = x1 :: x1_val;
                    y = y :: y_val;
                    }
                
                dataframe.DataFrame([x0, x1, y], columnNames: ["X", "Y", "Z"])
                }"""
            )(count, seed)



    def dataFrameFromMatrix(self, elt):
        return FORA.eval("""
            fun(math.Matrix(...) m) {
	        let colData = m.columnMajorData();

	        let nRows = m.dim[0];

	        dataframe.DataFrame(
		        Vector.range(
			        m.dim[1],
			        fun(colIx) { colData[colIx * nRows, (colIx + 1) * nRows] }
			        )
		        )
	        };""")(elt)

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

