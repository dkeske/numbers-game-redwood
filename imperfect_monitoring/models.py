# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from jsonfield import JSONField
from otree.api import models
from otree.constants import BaseConstants
from otree.models import BaseSubsession, BasePlayer
from otree_redwood.models import Event, DecisionGroup
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

    treatments = {
        'A': {
            'payoff_matrix': [
                [[100, 100], [0, 0]],
                [[125, 125], [25, 25]],
            ],
            'probability_matrix': [
                [[0.4, 0.4], [0.6, 0.6]],
                [[0.6, 0.6], [0.8, 0.8]],
            ],
            # [round(max(3, numpy.random.exponential(20))) for i in range(10)] 
            'num_subperiods': [
                7,
                3,
                29,
                11,
                9,
                6,
                6,
                3,
                6,
                13,
            ]
        }
    }


class Subsession(BaseSubsession):
    def before_session_starts(self):
        self.group_randomly()


class Group(DecisionGroup):

    state = models.CharField(max_length=10)
    t = models.PositiveIntegerField()
    fixed_group_decisions = JSONField()

    def period_length(self):
        num_subperiods = Constants.treatments[self.session.config['treatment']]['num_subperiods'][self.round_number-1]
        rest_length = self.session.config['rest_length']
        subperiod_length = self.session.config['subperiod_length']
        seconds_per_tick = self.session.config['seconds_per_tick']
        return (
            num_subperiods *
            ((subperiod_length + rest_length) * seconds_per_tick)
        )

    def when_all_players_ready(self):
        super().when_all_players_ready()

        self.state = 'results'
        self.t = 0
        self.fixed_group_decisions = {}
        for i, player in enumerate(self.get_players()):
            self.fixed_group_decisions[player.participant.code] = 0
        self.save()

        emitter = DiscreteEventEmitter(
            self.session.config['seconds_per_tick'], self.period_length(), self, self.tick)
        emitter.start()

    def tick(self, current_interval, intervals):
        # TODO: Integrate into the otree-redwood DiscreteEventEmitter API, because otherwise
        # someone will forget this and get very confused when the tick functions use stale data.
        self.refresh_from_db()
        msg = {}
        if self.state == 'results':
            msg = {
                'realizedPayoffs': self.realized_payoffs(),
                # TODO: We don't really want to send this to the subjects, but we do want it saved
                # in the event - do we need server-private event fields?
                'fixedDecisions' : self.fixed_group_decisions
            }
            self.t += 1
            if self.t == self.session.config['subperiod_length']:
                msg['showAverage'] = True
                msg['showPayoffBars'] = True
                self.state = 'pause'
                self.t = 0
        elif self.state == 'pause':
            msg = {
                'pauseProgress': (self.t+1)/self.session.config['rest_length']
            }
            self.t += 1
            if self.t == self.session.config['rest_length']:
                msg['clearCurrentSubperiod'] = True
                self.state = 'results'
                self.t = 0
                for i, player in enumerate(self.get_players()):
                    if player.participant.code in self.group_decisions:
                        self.fixed_group_decisions[player.participant.code] = self.group_decisions[player.participant.code]
        else:
            raise ValueError('invalid state {}'.format(self.state))

        self.send('tick', msg)
        self.save()


    def realized_payoffs(self):

        payoff_matrix = Constants.treatments[self.session.config['treatment']]['payoff_matrix']
        probability_matrix = Constants.treatments[self.session.config['treatment']]['probability_matrix']

        realized_payoffs = {}

        players = self.get_players()
        for i, player in enumerate(players):

            payoffs = [payoff_matrix[0][0][i], payoff_matrix[0][1][i], payoff_matrix[1][0][i], payoff_matrix[1][1][i]]
            probabilities = [probability_matrix[0][0][i], probability_matrix[0][1][i], probability_matrix[1][0][i], probability_matrix[1][1][i]]

            other = players[i-1]

            my_decision = self.fixed_group_decisions[player.participant.code]
            other_decision = self.fixed_group_decisions[other.participant.code]

            prob = ((my_decision * other_decision * probabilities[0]) +
                    (my_decision * (1 - other_decision) * probabilities[1]) +
                    ((1 - my_decision) * other_decision * probabilities[2]) +
                    ((1 - my_decision) * (1 - other_decision) * probabilities[3]))
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

    def initial_decision(self):
        return 0

    def other_player(self):
        return self.get_others_in_group()[0]

    def set_payoff(self):
        ticks = Event.objects.filter(
            channel='tick',
            content_type=ContentType.objects.get_for_model(self.group),
            group_pk=self.group.pk)
        
        self.payoff = 0
        total_subperiods = 0
        for tick in ticks:
            if 'realizedPayoffs' in tick.value:
                self.payoff += tick.value['realizedPayoffs'][self.participant.code]
                total_subperiods += 1
        if total_subperiods:
            self.payoff /= total_subperiods
