# -*- coding: utf-8 -*-
from __future__ import division
from ._builtin import Page, WaitPage
from .models import Constants


def vars_for_all_templates(self):
    return {
        "payoff_matrix": Constants.treatments[self.session.config['treatment']]['payoff_matrix'],
        "probability_matrix": Constants.treatments[self.session.config['treatment']]['probability_matrix'],
    }


class Introduction(Page):
    timeout_seconds = 100

    def is_displayed(self):
        return self.round_number == 1


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'


class Decision(Page):

    def vars_for_template(self):
        displayed_subperiods = self.session.config['displayed_subperiods'] 
        if displayed_subperiods == 0:
            displayed_subperiods = Constants.treatments[self.session.config['treatment']]['num_subperiods'][self.round_number-1]
        return {
            'displayed_subperiods': displayed_subperiods
        }


class Results(Page):

    def vars_for_template(self):
        self.player.set_payoff()
        return {}


def get_output_table(events):
    header = [
        'session_code',
        'subsession_id',
        'id_in_subsession',
        'timestamp',     
        'p1_code',
        'p2_code',
        'p1_strategy',
        'p2_strategy',
        'p1_realized_payoffs',
        'p2_realized_payoffs'
    ]
    if not events:
        return [], []
    rows = []
    p1, p2 = events[0].group.get_players()
    p1_code = p1.participant.code
    p2_code = p2.participant.code
    group = events[0].group
    for event in events:
        if event.channel == 'tick' and 'realizedPayoffs' in event.value:
            rows.append([
                group.session.code,
                group.subsession_id,
                group.id_in_subsession,
                event.timestamp,
                p1_code,
                p2_code,   
                event.value['fixedDecisions'][p1_code],
                event.value['fixedDecisions'][p2_code],
                event.value['realizedPayoffs'][p1_code],
                event.value['realizedPayoffs'][p2_code]
            ])
    return header, rows

page_sequence = [
        Introduction,
        DecisionWaitPage,
        Decision,
        Results
    ]
