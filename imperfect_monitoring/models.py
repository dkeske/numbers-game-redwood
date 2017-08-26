# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from jsonfield import JSONField
from otree.api import models
from otree.constants import BaseConstants
from otree.models import BaseSubsession, BasePlayer
from otree_redwood.models import Event, ContinuousDecisionGroup
from otree_redwood.utils import DiscreteEventEmitter
import random

doc = """
This is a Prisoner's Dilemna game with discrete time. Players are given two choices,
'Cooperate' or 'Don't Cooperate. Choices are distributed every N seconds, so players have
a "sub-period" of time to digest the results and strategize.
"""


class Constants(BaseConstants):
    name_in_url = 'imperfect_monitoring'
    players_per_group = 2
    num_rounds = 10

    #p1 payoffs
    p1_A_p2_A_amount = 100
    p1_A_p2_B_amount = 0
    p1_B_p2_A_amount = 125
    p1_B_p2_B_amount = 25

    #p2 payoffs
    p2_A_p1_A_amount = 100
    p2_A_p1_B_amount = 0
    p2_B_p1_A_amount = 125
    p2_B_p1_B_amount = 25

    #p1 signals
    p1_A_p2_A_signal = .4
    p1_A_p2_B_signal = .6
    p1_B_p2_A_signal = .6
    p1_B_p2_B_signal = .8

    #p2 signals
    p2_A_p1_A_signal = .4
    p2_A_p1_B_signal = .6
    p2_B_p1_A_signal = .6
    p2_B_p1_B_signal = .8

    base_points = 0

    # Amount of time the game stays on the decision page in seconds.
    num_subperiods = 10
    subperiod_length = 12

    # Number of discrete time subperiods in a single period.
 #   num_periods = 10

class Subsession(BaseSubsession):
    def before_session_starts(self):
        self.group_randomly()


class Group(ContinuousDecisionGroup):

    state = models.CharField(max_length=10)
    t = models.PositiveIntegerField()
    fixed_group_decisions = JSONField()

    def initial_decision(self):
        return 0

    def period_length(self):
        return Constants.num_subperiods * Constants.subperiod_length

    def when_all_players_ready(self):
        super().when_all_players_ready()

        self.state = 'results'
        self.t = 0
        self.fixed_group_decisions = {}
        for i, player in enumerate(self.get_players()):
            self.fixed_group_decisions[player.participant.code] = random.choice([1, 0])
        self.save()
        self.send('initialDecisions', self.fixed_group_decisions)

        emitter = DiscreteEventEmitter(.25, self.period_length(), self, self.tick)
        emitter.start()

    def tick(self, current_interval, intervals):
        msg = {}
        if self.state == 'results':
            msg = {
                'realizedPayoffs': self.realized_payoffs(),
                'fixedDecisions' : self.group_decisions
            }
        elif self.state == 'pause':
            if self.t == 6:
                msg = {
                    'updateStrategy': True,
                    'pauseProgress': 1/6.
                }
            else:
                msg = {
                    'pauseProgress': (self.t-5)/6.
                }
                if self.t == 11:
                    msg['clearGraph'] = True
        else:
            raise ValueError('invalid state {}'.format(self.state))

        self.send('tick', msg)

        self.t += 1
        if self.t == 6:
            self.state = 'pause'
        if self.t == 12:
            self.state = 'results'
            self.t = 0
            self.fixed_group_decisions = dict(self.group_decisions)
        self.save()


    def realized_payoffs(self):

        realized_payoffs = {}

        players = self.get_players()
        for i, player in enumerate(players):

            payoffs = None
            if i == 0:
                payoffs = [Constants.p1_A_p2_A_amount, Constants.p1_A_p2_B_amount, Constants.p1_B_p2_A_amount, Constants.p1_B_p2_B_amount]
                signals = [Constants.p1_A_p2_A_signal, Constants.p1_A_p2_B_signal, Constants.p1_B_p2_A_signal, Constants.p1_B_p2_B_signal]
            else:
                payoffs = [Constants.p2_A_p1_A_amount, Constants.p2_A_p1_B_amount, Constants.p2_B_p1_A_amount, Constants.p2_B_p1_B_amount]
                signals = [Constants.p2_A_p1_A_signal, Constants.p2_A_p1_B_signal, Constants.p2_B_p1_A_signal, Constants.p2_B_p1_B_signal]

            other = players[i-1]

            if self.fixed_group_decisions:
                my_decision = self.fixed_group_decisions[player.participant.code]
                other_decision = self.fixed_group_decisions[other.participant.code]
            else:
                my_decision = random.choice([0, 1])
                other_decision = random.choice([0, 1])

            prob = ((my_decision * other_decision * signals[0]) +
                    (my_decision * (1 - other_decision) * signals[1]) +
                    ((1 - my_decision) * other_decision * signals[2]) +
                    ((1 - my_decision) * (1 - other_decision) * signals[3]))
            payoff_index = 0
            if random.random() <= prob:
                if my_decision:
                    payoff_index = 1
                else:
                    payoff_index = 3
            else:
                if my_decision:
                    payoff_index = 0
                else:
                    payoff_index = 2

            realized_payoffs[player.participant.code] = payoffs[payoff_index]

        return realized_payoffs


class Player(BasePlayer):

    def other_player(self):
        return self.get_others_in_group()[0]

    def set_payoff(self):
        ticks = Event.objects.filter(
            channel='ticks',
            content_type=ContentType.objects.get_for_model(self.group),
            group_pk=self.group.pk)
        
        print(ticks)
        
        self.payoff = 0
        for tick in ticks:
            if 'realizedPayoffs' in tick.value:
                self.payoff += tick.value.realizedPayoffs[self.participant.code]
