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
        'p1_mean_strategy',
        'p2_mean_strategy',
        'p1_code',
        'p2_code',
    ]
    if not events:
        return [], []
    rows = []
    minT = min(e.timestamp for e in events)
    maxT = max(e.timestamp for e in events)
    last_p1_mean = float('nan')
    last_p2_mean = float('nan')
    p1, p2 = events[0].group.get_players()
    p1_code = p1.participant.code
    p2_code = p2.participant.code
    group = events[0].group
    if group.num_subperiods() is None:
        for tick in range((maxT - minT).seconds):
            currT = minT + timedelta(seconds=tick)
            group_decisions_events = []
            while events[0].timestamp <= currT:
                e = events.pop(0)
                if e.channel == 'group_decisions':
                    group_decisions_events.append(e)
            p1_decisions = []
            p2_decisions = []
            for event in group_decisions_events:
                p1_decisions.append(event.value[p1_code])
                p2_decisions.append(event.value[p2_code])
            p1_mean, p2_mean = last_p1_mean, last_p2_mean
            if p1_decisions:
                p1_mean = sum(p1_decisions) / len(p1_decisions)
            if p2_decisions:
                p2_mean = sum(p2_decisions) / len(p2_decisions)
            rows.append([
                group.session.code,
                group.subsession_id,
                group.id_in_subsession,
                tick,
                p1_mean,
                p2_mean,
                p1_code,
                p2_code,
            ])
            last_p1_mean = p1_mean
            last_p2_mean = p2_mean
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
