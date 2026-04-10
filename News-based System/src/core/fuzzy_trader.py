import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class FuzzyTrader:
    def __init__(self):
        # Inputs
        self.sentiment = ctrl.Antecedent(np.arange(-1, 1.1, 0.1), 'sentiment')
        self.conviction = ctrl.Antecedent(np.arange(0, 11, 1), 'conviction')
        self.materiality = ctrl.Antecedent(np.arange(0, 11, 1), 'materiality')
        self.persistence = ctrl.Antecedent(np.arange(0, 11, 1), 'persistence')

        # Output
        self.trade_signal = ctrl.Consequent(np.arange(-10, 11, 1), 'trade_signal')

        # Membership Functions
        self.sentiment.automf(names=['negative', 'neutral', 'positive'])
        self.conviction.automf(names=['low', 'medium', 'high'])
        self.materiality.automf(names=['low', 'medium', 'high'])
        self.persistence.automf(names=['short', 'medium', 'long'])

        self.trade_signal['strong_sell'] = fuzz.trimf(self.trade_signal.universe, [-10, -10, -6])
        self.trade_signal['sell'] = fuzz.trimf(self.trade_signal.universe, [-8, -4, 0])
        self.trade_signal['hold'] = fuzz.trimf(self.trade_signal.universe, [-2, 0, 2])
        self.trade_signal['buy'] = fuzz.trimf(self.trade_signal.universe, [0, 4, 8])
        self.trade_signal['strong_buy'] = fuzz.trimf(self.trade_signal.universe, [6, 10, 10])

        # Rules
        rule1 = ctrl.Rule(self.sentiment['positive'] & self.conviction['high'] & self.materiality['high'], self.trade_signal['strong_buy'])
        rule2 = ctrl.Rule(self.sentiment['positive'] & self.conviction['medium'], self.trade_signal['buy'])
        rule3 = ctrl.Rule(self.sentiment['positive'] & self.materiality['low'], self.trade_signal['hold']) # Ignore positive noise
        rule4 = ctrl.Rule(self.sentiment['negative'] & self.conviction['high'] & self.materiality['high'] & self.persistence['long'], self.trade_signal['strong_sell']) # Require structural change to sell
        rule5 = ctrl.Rule(self.sentiment['negative'] & self.materiality['low'], self.trade_signal['hold']) # Ignore negative noise
        rule6 = ctrl.Rule(self.sentiment['negative'] & self.conviction['medium'] & self.materiality['medium'], self.trade_signal['sell'])
        rule7 = ctrl.Rule(self.conviction['low'], self.trade_signal['hold'])
        rule8 = ctrl.Rule(self.sentiment['neutral'], self.trade_signal['hold'])

        self.trading_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8])
        self.trading_sim = ctrl.ControlSystemSimulation(self.trading_ctrl)

    def get_signal(self, sentiment_score, conviction_score, materiality_score, persistence_score):
        self.trading_sim.input['sentiment'] = sentiment_score
        self.trading_sim.input['conviction'] = conviction_score
        self.trading_sim.input['materiality'] = materiality_score
        self.trading_sim.input['persistence'] = persistence_score
        self.trading_sim.compute()
        return self.trading_sim.output['trade_signal']
