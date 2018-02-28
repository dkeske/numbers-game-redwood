from ._builtin import Page, WaitPage

from datetime import timedelta


class Introduction(Page):

    def is_displayed(self):
        return self.round_number == 1


class DecisionWaitPage(WaitPage):
    body_text = 'Waiting for all players to be ready'

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()


class Decision(Page):

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()
    

class Results(Page):
    timeout_seconds = 30

    def vars_for_template(self):
        self.player.set_payoff()
        return {}

    def is_displayed(self):
        return self.round_number <= self.group.num_rounds()


def get_output_table(events):
    header = [
        'session_code',
        'subsession_id',
        'id_in_subsession',
        'tick',
        'p1_strategy',
        'p2_strategy',
        'p1_code',
        'p2_code',
    ]
    if not events:
        return [], []
    rows = []
    minT = min(e.timestamp for e in events if e.channel == 'state')
    maxT = max(e.timestamp for e in events if e.channel == 'state')
    p1, p2 = events[0].group.get_players()
    p1_code = p1.participant.code
    p2_code = p2.participant.code
    group = events[0].group
    # sets sampling frequency for continuous time output
    ticks_per_second = 2
    if group.num_subperiods() == 0:
        p1_decision = float('nan')
        p2_decision = float('nan')
        for tick in range((maxT - minT).seconds * ticks_per_second):
            currT = minT + timedelta(seconds=(tick / ticks_per_second))
            cur_decision_event = None
            while events[0].timestamp <= currT:
                e = events.pop(0)
                if e.channel == 'group_decisions':
                    cur_decision_event = e
            if cur_decision_event:
                p1_decision = cur_decision_event.value[p1_code]
                p2_decision = cur_decision_event.value[p2_code]
            rows.append([
                group.session.code,
                group.subsession_id,
                group.id_in_subsession,
                tick,
                p1_decision,
                p2_decision,
                p1_code,
                p2_code,
            ])
    else:
        tick = 0
        for event in events:
            if event.channel == 'group_decisions':
                rows.append([
                    group.session.code,
                    group.subsession_id,
                    group.id_in_subsession,
                    tick,
                    event.value[p1_code],
                    event.value[p2_code],
                    p1_code,
                    p2_code,
                ])
                tick += 1
    return header, rows

page_sequence = [
    Introduction,
    DecisionWaitPage,
    Decision,
    Results
]
