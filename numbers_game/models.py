import csv
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
from numpy.random import uniform, normal
from numpy import mean, array_split, median
from scipy.stats import mode
from otree.db.models import Model, ForeignKey
from django.db.models.deletion import CASCADE
from random import shuffle
from otree_redwood.models import Group as RedwoodGroup


author = 'Daniel'

doc = """
Your app description
"""


def parse_config(config_file):
    with open('numbers_game/configs/' + config_file) as f:
        rows = list(csv.DictReader(f))

    rounds = []
    for row in rows:
        rounds.append({
            'group_size': row['group_size'],
            'distribution': row['distribution'],
            'feedback_view': row['feedback_view'],
            'decision_aggregation': row['decision_aggregation'],
        })
    return rounds


class Group(RedwoodGroup):

    def num_rounds(self):
        return len(parse_config(self.session.config['config_file']))

    group_policy = models.FloatField()

    def set_payoffs(self):
        for p in self.get_players():
            p.payoff = abs(p.assigned_number - self.group_policy)

    def _on_decision_event(self, event=None, **kwargs):
        # Extract data from the event
        chosen_num = event.value['chosen_num']
        id_in_group = event.value['oTree']['idInGroup']
        sender_player = self.get_player_by_id(id_in_group)
        sender_player.chosen_number = chosen_num
        sender_player.save()

        # Save new Decision model

        decision = sender_player.decision_set.create()  # create a new Decision object as part of the player's decision set
        decision.chosen_number = chosen_num
        decision.round_id = self.round_number
        decision.save()


        # Calculate group policy
        group_players = self.get_players()
        group_numbers = [p.chosen_number for p in group_players if p.chosen_number is not None]
        decision_aggregation = parse_config(self.session.config['config_file'])[self.round_number-1]['decision_aggregation']
        if decision_aggregation == 'MEAN':
            self.group_policy = mean(group_numbers)
        elif decision_aggregation == 'MEDIAN':
            self.group_policy = median(group_numbers)
        elif decision_aggregation == 'MODE':
            self.group_policy = mode(group_numbers)
        else:
            raise RuntimeError('Unrecognized parameter decision_aggregation from CONFIG file')
        event.value['group_policy'] = self.group_policy
        print(event.value)
        self.send("decision", event.value)


class Constants(BaseConstants):
    name_in_url = 'numbers_game'
    players_per_group = None
    num_rounds = 10
    num_decisions_per_round = 10
    endowment = c(10)
    min_number = c(0)
    max_number = c(20)
    min_chosen_num = c(0)
    max_chosen_num = c(20)


class Subsession(BaseSubsession):
    def before_session_starts(self):  # called each round
        # Used only for demo version
        # if 'config_file' not in self.session.config:
        #     self.session.config['config_file'] = 'demo.csv'
        print("Round number: ", self.round_number)
        if self.round_number > self.get_groups()[0].num_rounds():
            return
        distribution = parse_config(self.session.config['config_file'])[self.round_number - 1]['distribution']
        for p in self.get_players():
            if distribution == 'UNIFORM':
                p.assigned_number = uniform(int(Constants.min_number), int(Constants.max_number))
            elif distribution == 'NORMAL':
                # TODO change to actual distribution
                p.assigned_number = normal(int(Constants.min_number), int(Constants.max_number))
            else:
                raise RuntimeError('Unrecognized parameter DISTRIBUTION from CONFIG file')

    def creating_session(self):
        if self.round_number > self.get_groups()[0].num_rounds():
            return
        players_per_group = int(parse_config(self.session.config['config_file'])[self.round_number - 1]['group_size'])
        # matrix is a list of all participants
        matrix = self.get_group_matrix()
        print(matrix)
        number_of_participants = len(matrix[0])

        # Divide the participants in even size groups?
        if number_of_participants % players_per_group == 0:
            num_groups = number_of_participants // players_per_group
        else:
            # groups have to be of different sizes
            # it is the same because array_split does the heavy lifting
            num_groups = number_of_participants // players_per_group

        shuffle(matrix[0])
        print(matrix)
        print('Num groups: ', num_groups)
        new_matrix = array_split(matrix[0], num_groups)
        new_matrix = [list(a) for a in new_matrix]
        self.set_group_matrix(new_matrix)


class Player(BasePlayer):
    assigned_number = models.IntegerField()
    chosen_number = models.IntegerField(min=Constants.min_chosen_num, max=Constants.max_chosen_num)


class Decision(Model):  # our custom model inherits from Django's base class "Model"
    chosen_number = models.IntegerField()
    round_id = models.IntegerField()
    player = ForeignKey(Player, on_delete=CASCADE)  # creates 1:m relation -> this decision was made by a certain player
