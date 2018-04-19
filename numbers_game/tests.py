from otree.api import Currency as c, currency_range
from . import pages
from otree.api import Bot, SubmissionMustFail
from .models import Constants


class PlayerBot(Bot):

    def play_round(self):
        if self.player.id_in_group == 1:
            yield SubmissionMustFail(pages.WelcomePage, {'chosen_number': -1})
            yield (pages.WelcomePage, {'chosen_number': 15})
            # assert self.player.money_left == c(10)
        else:
            yield (pages.WelcomePage, {'chosen_number': 10})
        if self.round_number == Constants.num_rounds:
            yield (pages.Results)
