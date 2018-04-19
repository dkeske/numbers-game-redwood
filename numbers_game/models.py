from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency as c, currency_range
)
from numpy.random import uniform
from numpy import mean
from otree.db.models import Model, ForeignKey
from django.db.models.deletion import CASCADE
import random

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
        chosen_num = event.value['chosen_num']
        id_in_group = event.value['oTree']['idInGroup']
        sender_player = self.get_player_by_id(id_in_group)
        sender_player.chosen_number = chosen_num
        sender_player.save()

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
                # p.generate_decision_stubs()
                p.assigned_number = uniform(Constants.min_number, Constants.max_number)
        else:
            for p in self.get_players():
                p.assigned_number = p.in_round(1).assigned_number


# class Group(BaseGroup):
#     group_policy = models.FloatField()
#
#     def set_payoffs(self):
#         for p in self.get_players():
#             p.payoff = abs(p.assigned_number - self.group_policy)


class Player(BasePlayer):
    assigned_number = models.IntegerField()
    chosen_number = models.IntegerField(min=Constants.min_chosen_num, max=Constants.max_chosen_num)

    # def generate_decision_stubs(self):
    #     """
    #     Create a fixed number of "decision stubs", i.e. decision objects that only have a random "value" field on
    #     which the player will base her or his decision later in the game.
    #     """
    #     decision = self.decision_set.create()  # create a new Decision object as part of the player's decision set
    #     decision.value = random.randint(1, 10)  # don't forget to "import random" before!
    #     decision.save()  # important: save to DB!

# class Decision(Model):  # our custom model inherits from Django's base class "Model"
#     chosen_number = models.IntegerField()
#     player_decided = models.BooleanField()
#     round_id = models.IntegerField()
#     player = ForeignKey(Player, on_delete=CASCADE)  # creates 1:m relation -> this decision was made by a certain player
