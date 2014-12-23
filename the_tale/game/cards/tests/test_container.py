# coding: utf-8

import collections

import mock

from the_tale.common.utils import testcase

from the_tale.game.logic import create_test_map
from the_tale.game.logic_storage import LogicStorage

from the_tale.game.cards import container
from the_tale.game.cards import relations
from the_tale.game.cards import exceptions
from the_tale.game.cards import objects


class ContainerTests(testcase.TestCase):

    def setUp(self):
        super(ContainerTests, self).setUp()

        create_test_map()

        self.account = self.accounts_factory.create_account()

        self.storage = LogicStorage()
        self.storage.load_account_data(self.account)
        self.hero = self.storage.accounts_to_heroes[self.account.id]

        self.hero.cards._load_object()
        self.container = self.hero.cards._object


    def test_initialization(self):
        self.assertFalse(self.container.updated)
        self.assertEqual(self.container._cards, {})

    def test_serialization(self):
        self.container.add_card(objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON))
        self.container.add_card(objects.Card(relations.CARD_TYPE.ADD_GOLD_COMMON, available_for_auction=True))

        self.container.change_help_count(5)
        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True):
            self.container.change_help_count(3)

        self.assertEqual(self.container.serialize(), container.CardsContainer.deserialize(self.hero, self.container.serialize()).serialize())

    def test_add_card(self):
        self.assertFalse(self.container.updated)

        card_1 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        card_2 = objects.Card(relations.CARD_TYPE.ADD_GOLD_COMMON, available_for_auction=True)
        card_3 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_LEGENDARY)

        self.container.add_card(card_1)
        self.container.add_card(card_2)
        self.container.add_card(card_3)

        self.assertTrue(self.container.updated)
        self.assertEqual(self.container._cards, {card_1.uid: card_1,
                                                 card_2.uid: card_2,
                                                 card_3.uid: card_3})


    def test_remove_card(self):

        card_1 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        card_2 = objects.Card(relations.CARD_TYPE.ADD_GOLD_COMMON, available_for_auction=True)

        self.container.add_card(card_1)
        self.container.add_card(card_2)

        self.container.updated = False

        self.container.remove_card(card_1.uid)

        self.assertTrue(self.container.updated)
        self.assertEqual(self.container._cards, {card_2.uid: card_2})


    def test_card_count(self):
        self.assertEqual(self.container.card_count(relations.CARD_TYPE.KEEPERS_GOODS_COMMON), 0)

        card_1 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        card_2 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON, available_for_auction=True)
        card_3 = objects.Card(relations.CARD_TYPE.ADD_GOLD_COMMON, available_for_auction=True)

        self.container.add_card(card_1)
        self.container.add_card(card_2)
        self.container.add_card(card_3)

        self.assertEqual(self.container.card_count(relations.CARD_TYPE.KEEPERS_GOODS_COMMON), 2)
        self.assertEqual(self.container.card_count(relations.CARD_TYPE.ADD_GOLD_COMMON), 1)
        self.assertEqual(self.container.card_count(relations.CARD_TYPE.ADD_GOLD_RARE), 0)


    def test_has_cards(self):
        self.assertFalse(self.container.has_cards)
        self.container.add_card(objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON))
        self.assertTrue(self.container.has_cards)


    def test_change_help_count(self):
        self.assertEqual(self.container.help_count, 0)

        self.container.change_help_count(5)
        self.assertEqual(self.container._help_count, 5)
        self.assertEqual(self.container._premium_help_count, 0)

        with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True):
            self.container.change_help_count(4)
            self.assertEqual(self.container._help_count, 9)
            self.assertEqual(self.container._premium_help_count, 4)

            self.container.change_help_count(-3)
            self.assertEqual(self.container._help_count, 6)
            self.assertEqual(self.container._premium_help_count, 4)

            self.container.change_help_count(-3)
            self.assertEqual(self.container._help_count, 3)
            self.assertEqual(self.container._premium_help_count, 3)

        self.container.change_help_count(2)
        self.assertEqual(self.container._help_count, 5)
        self.assertEqual(self.container._premium_help_count, 3)

        self.container.change_help_count(-5)
        self.assertEqual(self.container._help_count, 0)
        self.assertEqual(self.container._premium_help_count, 0)

    def test_change_help_count__below_zero(self):
        self.assertRaises(exceptions.HelpCountBelowZero, self.container.change_help_count, -5)


    def test_get_card_for_use__no_card(self):
        self.assertEqual(self.container.get_card_for_use(relations.CARD_TYPE.KEEPERS_GOODS_COMMON), None)


    def test_get_card_for_use__no_card__not_auction_first(self):
        card_1 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        card_2 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON, available_for_auction=True)
        card_3 = objects.Card(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)

        self.container.add_card(card_1)
        self.container.add_card(card_2)
        self.container.add_card(card_3)

        card = self.container.get_card_for_use(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        self.assertIn(card.uid, (card_1.uid, card_3.uid))
        self.container.remove_card(card.uid)

        card = self.container.get_card_for_use(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        self.assertIn(card.uid, (card_1.uid, card_3.uid))
        self.container.remove_card(card.uid)

        card = self.container.get_card_for_use(relations.CARD_TYPE.KEEPERS_GOODS_COMMON)
        self.assertEqual(card.uid, card_2.uid)



class GetNewCardTest(testcase.TestCase):

    def setUp(self):
        super(GetNewCardTest, self).setUp()

        create_test_map()

        self.account = self.accounts_factory.create_account()

        self.storage = LogicStorage()
        self.storage.load_account_data(self.account)
        self.hero = self.storage.accounts_to_heroes[self.account.id]


    def test_single_card(self):
        self.assertTrue(self.hero.cards.has_card(self.hero.cards.get_new_card().type))


    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True)
    def test_simple(self):

        rarities = set()

        for i in xrange(len(relations.CARD_TYPE.records)*1000):
            card = self.hero.cards.get_new_card()
            rarities.add(card.type.rarity)

        self.assertEqual(len(relations.CARD_TYPE.records), len(set(card.type for card in self.hero.cards.all_cards())))
        self.assertEqual(rarities, set(relations.RARITY.records))

    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', False)
    def test_not_premium(self):

        for i in xrange(len(relations.CARD_TYPE.records)*10):
            self.hero.cards.get_new_card()

        for card in relations.CARD_TYPE.records:
            if self.hero.cards.has_card(card):
                self.assertFalse(card.availability.is_FOR_PREMIUMS)

    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True)
    def test_priority(self):
        for i in xrange(len(relations.CARD_TYPE.records)*1000):
            self.hero.cards.get_new_card()

        rarities = collections.Counter(card.type.rarity for card in self.hero.cards.all_cards())

        last_rarity_count = 999999999999

        for rarity in relations.RARITY.records:
            self.assertTrue(last_rarity_count >= rarities[rarity])
            last_rarity_count = rarities[rarity]

    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True)
    def test_rarity(self):
        for rarity in relations.RARITY.records:
            for i in xrange(100):
                card = self.hero.cards.get_new_card(rarity=rarity)
                self.assertEqual(card.type.rarity, rarity)


    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.is_premium', True)
    def test_exclude(self):
        cards = set()

        for i in xrange(len(relations.CARD_TYPE.records)):
            cards.add(self.hero.cards.get_new_card(exclude=cards).type)

        self.assertEqual(cards, set(relations.CARD_TYPE.records))


class CanCombineCardsTests(testcase.TestCase):

    def setUp(self):
        super(CanCombineCardsTests, self).setUp()

        create_test_map()

        self.account = self.accounts_factory.create_account()

        self.storage = LogicStorage()
        self.storage.load_account_data(self.account)
        self.hero = self.storage.accounts_to_heroes[self.account.id]

        self.card__add_power_common_1 = objects.Card(type=relations.CARD_TYPE.ADD_POWER_COMMON)
        self.card__add_power_common_2 = objects.Card(type=relations.CARD_TYPE.ADD_POWER_COMMON)
        self.card__add_power_common_3 = objects.Card(type=relations.CARD_TYPE.ADD_POWER_COMMON)
        self.card__add_power_common_4 = objects.Card(type=relations.CARD_TYPE.ADD_POWER_COMMON)

        self.card__add_bonus_energy_common_1 = objects.Card(type=relations.CARD_TYPE.ADD_BONUS_ENERGY_COMMON)

        self.card__add_bonus_energy_legendary_1 = objects.Card(type=relations.CARD_TYPE.ADD_BONUS_ENERGY_LEGENDARY)
        self.card__add_bonus_energy_legendary_2 = objects.Card(type=relations.CARD_TYPE.ADD_BONUS_ENERGY_LEGENDARY)
        self.card__add_bonus_energy_legendary_3 = objects.Card(type=relations.CARD_TYPE.ADD_BONUS_ENERGY_LEGENDARY)

        self.card__add_gold_common_1 = objects.Card(type=relations.CARD_TYPE.ADD_GOLD_COMMON)

        self.hero.cards.add_card(self.card__add_power_common_1)
        self.hero.cards.add_card(self.card__add_power_common_2)
        self.hero.cards.add_card(self.card__add_power_common_3)
        self.hero.cards.add_card(self.card__add_power_common_4)

        self.hero.cards.add_card(self.card__add_bonus_energy_common_1)

        self.hero.cards.add_card(self.card__add_bonus_energy_legendary_1)
        self.hero.cards.add_card(self.card__add_bonus_energy_legendary_2)
        self.hero.cards.add_card(self.card__add_bonus_energy_legendary_3)

        self.hero.cards.add_card(self.card__add_gold_common_1)


    def test_not_enough_cards(self):
        self.assertTrue(self.hero.cards.can_combine_cards([]).is_NOT_ENOUGH_CARDS)
        self.assertTrue(self.hero.cards.can_combine_cards([]).is_NOT_ENOUGH_CARDS)
        self.assertFalse(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                            self.card__add_power_common_2.uid]).is_NOT_ENOUGH_CARDS)

    def test_to_many_cards(self):
        self.assertFalse(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                            self.card__add_power_common_2.uid]).is_TO_MANY_CARDS)
        self.assertFalse(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                            self.card__add_power_common_2.uid,
                                                            self.card__add_power_common_3.uid]).is_TO_MANY_CARDS)
        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_power_common_2.uid,
                                                           self.card__add_power_common_3.uid,
                                                           self.card__add_power_common_4.uid]).is_TO_MANY_CARDS)

    def test_equal_rarity_required(self):
        self.assertNotEqual(self.card__add_power_common_1.type.rarity, self.card__add_bonus_energy_legendary_1.type.rarity)
        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_bonus_energy_legendary_1.uid]).is_EQUAL_RARITY_REQUIRED)

        self.assertEqual(self.card__add_power_common_1.type.rarity, self.card__add_bonus_energy_common_1.type.rarity)
        self.assertFalse(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                            self.card__add_bonus_energy_common_1.uid]).is_EQUAL_RARITY_REQUIRED)

    def test_legendary_x3(self):
        self.assertTrue(self.card__add_bonus_energy_legendary_1.type.rarity.is_LEGENDARY)
        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_bonus_energy_legendary_1.uid,
                                                           self.card__add_bonus_energy_legendary_2.uid,
                                                           self.card__add_bonus_energy_legendary_3.uid]).is_LEGENDARY_X3_DISALLOWED)
        self.assertFalse(self.hero.cards.can_combine_cards([self.card__add_bonus_energy_legendary_1.uid,
                                                           self.card__add_bonus_energy_legendary_2.uid]).is_LEGENDARY_X3_DISALLOWED)


    def test_no_cards(self):
        self.assertTrue(self.hero.cards.can_combine_cards([666, 667]).is_HAS_NO_CARDS)
        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1, 667]).is_HAS_NO_CARDS)
        self.assertTrue(self.hero.cards.can_combine_cards([666, self.card__add_power_common_1]).is_HAS_NO_CARDS)


    def test_allowed(self):
        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_power_common_2.uid,]).is_ALLOWED)

        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_power_common_2.uid,
                                                           self.card__add_bonus_energy_common_1.uid]).is_ALLOWED)

        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_power_common_2.uid,
                                                           self.card__add_power_common_3.uid]).is_ALLOWED)

        self.assertTrue(self.hero.cards.can_combine_cards([self.card__add_power_common_1.uid,
                                                           self.card__add_bonus_energy_common_1.uid,
                                                           self.card__add_gold_common_1.uid]).is_ALLOWED)
