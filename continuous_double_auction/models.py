# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from jsonfield import JSONField
from otree.api import models
from otree.constants import BaseConstants
from otree.models import BaseSubsession, BasePlayer
from otree_redwood.models import Event, Group as RedwoodGroup
import random

doc = """
"""


class Constants(BaseConstants):
    name_in_url = 'continuous_double_auction'
    players_per_group = None
    num_rounds = 10


class Subsession(BaseSubsession):

    def before_session_starts(self):
        self.group_randomly()
        for player in self.get_players():
            if player.role() == 'buyer':
                player.currency = 100
            else:
                player.units = 6


class Group(RedwoodGroup):

    bid_queue = JSONField()
    ask_queue = JSONField()

    def period_length(self):
        return 1200

    def get_player(self, pcode):
        for player in self.get_players():
            if player.participant.code == pcode:
                return player
        return None

    def trade(self, buyer=None, seller=None, price=None):
        buyer.currency -= price
        buyer.units += 1
        seller.currency += price
        seller.units -= 1
        buyer.save()
        seller.save()

    def _on_market_event(self, event):
        if not self.bid_queue:
            self.bid_queue = []
        if not self.ask_queue:
            self.ask_queue = []

        player = self.get_player(event.participant.code)
        role = player.role()

        if event.value['type'] == 'bid':
            if role != 'buyer':
                return
            if event.value['price'] > player.currency:
                return
            found = False
            for bid in self.bid_queue:
                if bid['pcode'] == event.participant.code:
                    bid['price'] = event.value['price']
                    found = True
            if not found:
                if self.ask_queue and event.value['price'] >= self.ask_queue[0]['price']:
                    ask = self.ask_queue.pop(0)
                    self.trade(
                        buyer=player,
                        seller=self.get_player(ask['pcode']),
                        price=ask['price'])
                else:
                    self.bid_queue.append({
                        'price': event.value['price'],
                        'pcode': event.participant.code,
                    })
                    self.bid_queue = sorted(
                        self.bid_queue,
                        key=lambda bid: bid['price'],
                        reverse=True)

        if event.value['type'] == 'ask':
            if role != 'seller':
                return
            if player.units <= 0:
                return
            found = False
            for ask in self.ask_queue:
                if ask['pcode'] == event.participant.code:
                    ask['price'] = event.value['price']
                    found = True
            if not found:
                if self.bid_queue and event.value['price'] <= self.bid_queue[0]['price']:
                    bid = self.bid_queue.pop(0)
                    self.trade(
                        buyer=self.get_player(bid['pcode']),
                        seller=player,
                        price=bid['price'])
                else:
                    self.ask_queue.append({
                        'price': event.value['price'],
                        'pcode': event.participant.code,
                    })
                    self.ask_queue = sorted(
                        self.ask_queue,
                        key=lambda ask: ask['price'])

        if event.value['type'] == 'remove':
            found = None
            for i, bid in enumerate(self.bid_queue):
                if bid['pcode'] == event.participant.code:
                    found = i
            if found is not None:
                self.bid_queue.pop(found)
            found = None
            for i, ask in enumerate(self.ask_queue):
                if ask['pcode'] == event.participant.code:
                    found = i
            if found is not None:
                self.ask_queue.pop(found)

        if event.value['type'] == 'buy':
            if role != 'buyer':
                return
            if self.ask_queue and player.currency >= self.ask_queue[0]['price']:
                ask = self.ask_queue.pop(0)
                self.trade(
                    buyer=player,
                    seller=self.get_player(ask['pcode']),
                    price=ask['price'])

        if event.value['type'] == 'sell':
            if role != 'seller':
                return
            if self.bid_queue and player.units > 0:
                bid = self.bid_queue.pop(0)
                self.trade(
                    buyer=self.get_player(bid['pcode']),
                    seller=player,
                    price=bid['price'])

        self.save()
        self.send('market', {
            'bid_queue': self.bid_queue,
            'ask_queue': self.ask_queue,
        })


class Player(BasePlayer):

    currency = models.IntegerField(initial=0)
    units = models.IntegerField(initial=0)

    def role(self):
        if self.id_in_group % 2 == 0:
            return 'buyer'
        else:
            return 'seller'

    def value(self):
        if self.role() == 'buyer':
            return 25
        return None

    def cost(self):
        if self.role() == 'seller':
            return 10
        return None

    def set_payoff(self):
        self.payoff = 0
