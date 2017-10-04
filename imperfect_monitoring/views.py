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
        return {}


class Results(Page):

    def vars_for_template(self):
        self.player.set_payoff()
        return {}


def get_output_table(events):
    table = []
    for e in events:
        if e.channel == 'decisions':
            table.append(e.value),
            table.append(e.participant.code) 
        if e.channel == 'tick':
            if 'realizedPayoffs' in e.value:
                table.append(e.value ['realizedPayoffs'])
            if 'fixedDecisions' in e.value:
                table.append(e.value ['fixedDecisions'])
    print(table)
    return table


page_sequence = [
        Introduction,
        DecisionWaitPage,
        Decision,
        Results
    ]
