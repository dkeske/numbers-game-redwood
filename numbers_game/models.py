from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
from numpy.random import uniform, normal
from numpy import mean, array_split
from otree.db.models import Model, ForeignKey
from django.db.models.deletion import CASCADE
from random import shuffle

from otree_redwood.models import Group as RedwoodGroup


author = 'Daniel'

doc = """
Your app description
"""


class Group(RedwoodGroup):
    group_policy = models.FloatField()

    def set_payoffs(self):
        for p in self.get_players():
            p.payoff = abs(p.assigned_number - self.group_policy)

    def _on_decision_event(self, event=None, **kwargs):
        # Extract data from the event
        # TODO save the player decisions
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
        self.group_policy = mean(group_numbers)
        event.value['group_policy'] = self.group_policy
        print(event.value)
        self.send("decision", event.value)


class Constants(BaseConstants):
    name_in_url = 'numbers_game'
    players_per_group = None
    num_rounds = 3
    num_decisions_per_round = 10
    endowment = c(10)
    min_number = c(0)
    max_number = c(20)
    min_chosen_num = c(0)
    max_chosen_num = c(20)



class Subsession(BaseSubsession):
    def before_session_starts(self):  # called each round
        """For each player, create a fixed number of "decision stubs" with random values to be decided upon later."""
        if self.round_number == 1:
            for p in self.get_players():
                # TODO change to config
                # if self.session.vars['number_distribution'] == 'uniform':
                if True:
                    p.assigned_number = uniform(int(Constants.min_number), int(Constants.max_number))
                # TODO change to actual distribution
                # elif self.session.vars['number_distribution'] == 'normal':
                #     p.assigned_number = normal(int(Constants.min_number), int(Constants.max_number))
        else:
            for p in self.get_players():
                p.assigned_number = p.in_round(1).assigned_number

    def creating_session(self):
        self.session.vars['players_per_group'] = 3 #TODO change to config
        players_per_group = self.session.vars['players_per_group']
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
        new_matrix = array_split(matrix[0], num_groups)
        new_matrix = [list(a) for a in new_matrix]
        self.set_group_matrix(new_matrix)


class Player(BasePlayer):
    assigned_number = models.IntegerField()
    chosen_number = models.IntegerField(min=Constants.min_chosen_num, max=Constants.max_chosen_num)

   # important: save to DB!


class Decision(Model):  # our custom model inherits from Django's base class "Model"
    chosen_number = models.IntegerField()
    round_id = models.IntegerField()
    player = ForeignKey(Player, on_delete=CASCADE)  # creates 1:m relation -> this decision was made by a certain player
