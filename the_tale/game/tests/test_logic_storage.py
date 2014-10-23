# coding: utf-8
import mock
import datetime

from the_tale.common.utils import testcase

from the_tale.accounts.prototypes import AccountPrototype
from the_tale.accounts.logic import register_user

from the_tale.game.heroes.prototypes import HeroPrototype

from the_tale.game.actions import prototypes as actions_prototypes
from the_tale.game.actions.meta_actions import MetaActionArenaPvP1x1Prototype

from the_tale.game.logic import create_test_map
from the_tale.game.logic_storage import LogicStorage
from the_tale.game import exceptions
from the_tale.game.prototypes import TimePrototype
from the_tale.game.bundles import BundlePrototype


class LogicStorageTestsBasic(testcase.TestCase):

    def setUp(self):
        super(LogicStorageTestsBasic, self).setUp()

        self.p1, self.p2, self.p3 = create_test_map()

        self.storage = LogicStorage()


    def test_initialize(self):
        self.assertEqual(self.storage.heroes, {})
        self.assertEqual(self.storage.meta_actions, {})
        self.assertEqual(self.storage.meta_actions_to_actions, {})
        self.assertEqual(self.storage.skipped_heroes, set())
        self.assertEqual(self.storage.accounts_to_heroes, {})


class LogicStorageTests(testcase.TestCase):

    def setUp(self):
        super(LogicStorageTests, self).setUp()

        self.p1, self.p2, self.p3 = create_test_map()

        self.storage = LogicStorage()

        result, account_1_id, bundle_1_id = register_user('test_user_1', 'test_user_1@test.com', '111111')
        result, account_2_id, bundle_2_id = register_user('test_user_2', 'test_user_2@test.com', '111111')

        self.bundle_1_id = bundle_1_id
        self.bundle_2_id = bundle_2_id

        self.account_1 = AccountPrototype.get_by_id(account_1_id)
        self.account_2 = AccountPrototype.get_by_id(account_2_id)

        self.storage.load_account_data(AccountPrototype.get_by_id(account_1_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_2_id))

        self.hero_1 = self.storage.accounts_to_heroes[account_1_id]
        self.hero_2 = self.storage.accounts_to_heroes[account_2_id]

        self.action_idl_1 = self.hero_1.actions.current_action
        self.action_idl_2 = self.hero_2.actions.current_action

    def test_load_account_data(self):
        self.assertEqual(len(self.storage.heroes), 2)
        self.assertEqual(len(self.storage.accounts_to_heroes), 2)
        self.assertEqual(self.storage.bundles_to_accounts, {self.hero_1.actions.current_action.bundle_id: set([self.account_1.id]),
                                                            self.hero_2.actions.current_action.bundle_id: set([self.account_2.id])})

        action_regenerate = actions_prototypes.ActionRegenerateEnergyPrototype.create(hero=self.hero_1)

        self.assertEqual(self.action_idl_1.storage, self.storage)
        self.assertEqual(action_regenerate.storage, self.storage)

        storage = LogicStorage()
        storage.load_account_data(AccountPrototype.get_by_id(self.account_1.id))
        storage.load_account_data(AccountPrototype.get_by_id(self.account_2.id))
        self.assertEqual(len(storage.heroes), 2)
        self.assertEqual(len(storage.accounts_to_heroes), 2)
        self.assertEqual(storage.bundles_to_accounts, {self.hero_1.actions.current_action.bundle_id: set([self.account_1.id]),
                                                       self.hero_2.actions.current_action.bundle_id: set([self.account_2.id])})


    def test_load_account_data_with_meta_action(self):
        bundle = BundlePrototype.create()

        meta_action_battle = MetaActionArenaPvP1x1Prototype.create(self.storage, self.hero_1, self.hero_2, bundle=bundle)

        proxy_action_1 = actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_1, _bundle_id=bundle.id, meta_action=meta_action_battle)
        proxy_action_2 = actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_2, _bundle_id=bundle.id, meta_action=meta_action_battle)

        self.assertEqual(len(self.storage.meta_actions), 1)
        self.assertEqual(len(self.storage.meta_actions_to_actions), 1)
        self.assertEqual(self.storage.meta_actions_to_actions[meta_action_battle.id], set([LogicStorage.get_action_uid(proxy_action_1),
                                                                                           LogicStorage.get_action_uid(proxy_action_2)]))

        self.storage.save_changed_data()

        storage = LogicStorage()
        storage.load_account_data(AccountPrototype.get_by_id(self.account_1.id))
        storage.load_account_data(AccountPrototype.get_by_id(self.account_2.id))

        self.assertEqual(len(storage.meta_actions), 1)
        self.assertEqual(len(storage.meta_actions_to_actions), 1)
        self.assertEqual(storage.meta_actions_to_actions[meta_action_battle.id], set([LogicStorage.get_action_uid(proxy_action_1),
                                                                                      LogicStorage.get_action_uid(proxy_action_2)]))

        self.assertEqual(storage.bundles_to_accounts, {self.hero_1.actions.current_action.bundle_id: set([self.account_1.id, self.account_2.id])})


    def test_add_duplicate_hero(self):
        self.assertRaises(exceptions.HeroAlreadyRegisteredError, self.storage._add_hero, self.hero_1)


    def test_action_release_account_data(self):

        actions_prototypes.ActionRegenerateEnergyPrototype.create(hero=self.hero_1)

        self.storage.skipped_heroes.add(self.hero_1.id)

        self.storage.release_account_data(AccountPrototype.get_by_id(self.account_1.id))

        self.assertEqual(len(self.storage.heroes), 1)
        self.assertEqual(len(self.storage.accounts_to_heroes), 1)
        self.assertEqual(self.storage.bundles_to_accounts, {self.hero_2.actions.current_action.bundle_id: set([self.account_2.id])})
        self.assertEqual(self.storage.heroes.values()[0].id, self.hero_2.id)
        self.assertFalse(self.storage.skipped_heroes)

    def test_save_hero_data(self):

        self.hero_1.health = 1
        self.hero_2.health = 1

        self.hero_1.actions.updated = True

        self.storage._save_hero_data(self.hero_1.id, update_cache=False)

        self.assertEqual(self.hero_1.health, HeroPrototype.get_by_id(self.hero_1.id).health)
        self.assertNotEqual(self.hero_2.health, HeroPrototype.get_by_id(self.hero_2.id).health)

        self.assertFalse(self.hero_1.actions.updated)

    def test_save_all(self):

        self.hero_1.health = 1
        self.hero_2.health = 1

        self.hero_1.actions.updated = True

        self.storage.save_all()

        self.assertEqual(self.hero_1.health, HeroPrototype.get_by_id(self.hero_1.id).health)
        self.assertEqual(self.hero_2.health, HeroPrototype.get_by_id(self.hero_2.id).health)

        self.assertFalse(self.hero_1.actions.updated)

    def test_save_hero_data_with_meta_action(self):
        bundle = BundlePrototype.create()

        meta_action_battle = MetaActionArenaPvP1x1Prototype.create(self.storage, self.hero_1, self.hero_2, bundle=bundle)

        actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_1, _bundle_id=bundle.id, meta_action=meta_action_battle)
        actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_2, _bundle_id=bundle.id, meta_action=meta_action_battle)

        with mock.patch('the_tale.game.actions.meta_actions.MetaActionPrototype.save') as save_counter:
            self.storage._save_hero_data(self.hero_1.id, update_cache=False)
            self.storage._save_hero_data(self.hero_2.id, update_cache=False)

        self.assertEqual(save_counter.call_count, 0)

        self.storage.meta_actions.values()[0].updated = True
        with mock.patch('the_tale.game.actions.meta_actions.MetaActionPrototype.save', save_counter):
            self.storage._save_hero_data(self.hero_1.id, update_cache=False)
            self.storage._save_hero_data(self.hero_2.id, update_cache=False)

        self.assertEqual(save_counter.call_count, 0) # meta action saved by proxy actions

        self.hero_1.actions.updated = True
        self.hero_2.actions.updated = True

        with mock.patch('the_tale.game.actions.meta_actions.MetaActionPrototype.save', save_counter):
            self.storage._save_hero_data(self.hero_1.id, update_cache=False)
            self.storage._save_hero_data(self.hero_2.id, update_cache=False)

        self.assertEqual(save_counter.call_count, 2) # meta action saved by every proxy actions (see mock.patch)


    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    def test_process_turn(self):
        self.assertEqual(self.storage.skipped_heroes, set())
        self.storage.process_turn()
        self.assertEqual(self.storage.skipped_heroes, set())

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
            self.storage.save_changed_data()

        self.assertEqual(save_hero_data.call_count, 2)

    def test_process_turn_single_hero__runned_outside_storage(self):
        action_1 = actions_prototypes.ActionRegenerateEnergyPrototype.create(hero=self.hero_1)
        action_1.state = action_1.STATE.PROCESSED

        action_2 = actions_prototypes.ActionMoveToPrototype.create(hero=self.hero_1, destination=self.p1)
        action_2.state = action_2.STATE.PROCESSED

        action_3 = actions_prototypes.ActionInPlacePrototype.create(hero=self.hero_1)
        action_3.state = action_3.STATE.PROCESSED

        self.assertEqual(self.hero_1.actions.number, 4)

        self.storage.process_turn__single_hero(hero=self.hero_1,
                                               logger=None,
                                               continue_steps_if_needed=True)

        self.assertEqual(self.hero_1.actions.number, 2)
        self.assertEqual(self.hero_1.actions.current_action.TYPE, actions_prototypes.ActionQuestPrototype.TYPE)

        self.storage.process_turn() # just nothing was broken


    def test_process_turn__process_action_chain(self):
        action_1 = actions_prototypes.ActionRegenerateEnergyPrototype.create(hero=self.hero_1)
        action_1.state = action_1.STATE.PROCESSED

        action_2 = actions_prototypes.ActionMoveToPrototype.create(hero=self.hero_1, destination=self.p1)
        action_2.state = action_2.STATE.PROCESSED

        action_3 = actions_prototypes.ActionInPlacePrototype.create(hero=self.hero_1)
        action_3.state = action_3.STATE.PROCESSED

        self.assertEqual(self.hero_1.actions.number, 4)

        self.storage.process_turn()

        self.assertEqual(self.hero_1.actions.number, 2)
        self.assertEqual(self.hero_1.actions.current_action.TYPE, actions_prototypes.ActionQuestPrototype.TYPE)


    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', False)
    def test_process_turn__without_dump(self):
        self.assertEqual(self.storage.skipped_heroes, set())
        self.storage.process_turn()
        self.assertEqual(self.storage.skipped_heroes, set())

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
            self.storage.save_changed_data()

        self.assertEqual(save_hero_data.call_count, 1) # save only game_settings.SAVED_UNCACHED_HEROES_FRACTION bundles number


    def test_process_turn__process_created_action(self):
        from the_tale.game.actions.prototypes import ActionMoveToPrototype

        place = self.p1

        def process_action(self):
            ActionMoveToPrototype.create(hero=self.hero, destination=place)

        with mock.patch('the_tale.game.actions.prototypes.ActionIdlenessPrototype.process', process_action):
            with mock.patch('the_tale.game.actions.prototypes.ActionMoveToPrototype.process') as move_to_process:
                self.storage.process_turn()

        self.assertEqual(move_to_process.call_count, 2)

    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    def test_process_turn_with_skipped_hero(self):
        # skipped heroes saved, but not processed
        self.storage.skipped_heroes.add(self.hero_1.id)

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.process_turn') as action_process_turn:
            self.storage.process_turn()

        self.assertEqual(action_process_turn.call_count, 1)

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
            self.storage.save_changed_data()

        self.assertEqual(save_hero_data.call_count, 2)

    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', False)
    def test_process_turn_with_skipped_hero__without_cache_dump(self):
        # skipped heroes saved, but not processed
        self.storage.skipped_heroes.add(self.hero_1.id)

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.process_turn') as action_process_turn:
            self.storage.process_turn()

        self.assertEqual(action_process_turn.call_count, 1)

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
            self.storage.save_changed_data()

        self.assertEqual(save_hero_data.call_count, 1)

    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.can_process_turn', lambda self, turn: True)
    def test_process_turn__can_process_turn(self):
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.process_turn') as action_process_turn:
            self.storage.process_turn(continue_steps_if_needed=False)

        self.assertEqual(action_process_turn.call_count, 2)

    @mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.can_process_turn', lambda self, turn: False)
    def test_process_turn__can_not_process_turn(self):
        with mock.patch('the_tale.game.actions.prototypes.ActionBase.process_turn') as action_process_turn:
            self.storage.process_turn(continue_steps_if_needed=False)

        self.assertEqual(action_process_turn.call_count, 0)

    def test_process_turn___exception_raises(self):
        def process_turn_raise_exception(action):
            if action.hero.id == self.hero_2.id:
                raise Exception('error')

        with mock.patch('the_tale.game.actions.prototypes.ActionBase.process_turn', process_turn_raise_exception):
            with mock.patch('the_tale.game.logic_storage.LogicStorage._save_on_exception') as _save_on_exception:
                self.assertRaises(Exception, self.storage.process_turn)

        self.assertEqual(_save_on_exception.call_count, 1)
        self.assertEqual(_save_on_exception.call_args, mock.call(excluded_bundle_id=self.hero_2.id))

    def test_save_on_exception(self):
        # hero 1 not saved due to one bundle with hero 3
        # hero 2 saved
        # hero 3 not saved
        # hero 4 saved

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')
        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))
        hero_3 = self.storage.accounts_to_heroes[account_3_id]

        result, account_4_id, bundle_4_id = register_user('test_user_4', 'test_user_4@test.com', '111111')
        self.storage.load_account_data(AccountPrototype.get_by_id(account_4_id))
        hero_4 = self.storage.accounts_to_heroes[account_4_id]

        self.hero_1.actions.current_action.bundle_id = hero_3.actions.current_action.bundle_id

        saved_heroes = set()

        def save_hero_data(storage, hero_id, **kwargs):
            saved_heroes.add(hero_id)

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data', save_hero_data):
            self.storage._save_on_exception(hero_3.actions.current_action.bundle_id)

        self.assertEqual(saved_heroes, set([self.hero_2.id, hero_4.id]))


    def test_save_changed_data(self):
        self.storage.process_turn()

        with mock.patch('dext.common.utils.cache.set_many') as set_many:
            with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                self.storage.save_changed_data()

        self.assertEqual(set_many.call_count, 1)
        self.assertEqual(ui_info.call_count, 2)
        self.assertEqual(ui_info.call_args, mock.call(actual_guaranteed=True))

    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    def test_save_changed_data__with_unsaved_bundles(self):
        self.storage.process_turn()

        self.assertEqual(len(self.storage.heroes), 2)

        with mock.patch('the_tale.game.logic_storage.LogicStorage._get_bundles_to_save', lambda x: [self.bundle_2_id]):
            with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
                with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                    self.storage.save_changed_data()

        self.assertEqual(ui_info.call_count, 2) # cache all heroes, since they are new
        self.assertEqual(ui_info.call_args, mock.call(actual_guaranteed=True))
        self.assertEqual(save_hero_data.call_args, mock.call(self.hero_2.id, update_cache=False))

    def test_save_changed_data__with_unsaved_bundles__without_dump(self):
        self.storage.process_turn()

        self.assertEqual(len(self.storage.heroes), 2)

        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        with mock.patch('the_tale.game.logic_storage.LogicStorage._get_bundles_to_save', lambda x: [self.bundle_2_id]):
            with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
                with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                    self.storage.save_changed_data()

        self.assertEqual(ui_info.call_count, 1) # cache only first hero
        self.assertEqual(ui_info.call_args, mock.call(actual_guaranteed=True))
        self.assertEqual(save_hero_data.call_args, mock.call(self.hero_2.id, update_cache=False))

    def test__destroy_account_data(self):
        from the_tale.game.heroes.models import Hero

        current_time = TimePrototype.get_current_time()

        # make some actions
        while self.hero_1.position.place is not None:
            self.storage.process_turn()
            current_time.increment_turn()

        self.assertEqual(Hero.objects.all().count(), 2)

        self.storage._destroy_account_data(self.account_1)
        self.storage._destroy_account_data(self.account_2)

        self.assertEqual(Hero.objects.all().count(), 0)

    def test_remove_action__from_middle(self):
        actions_prototypes.ActionRegenerateEnergyPrototype.create(hero=self.hero_1)
        self.assertRaises(exceptions.RemoveActionFromMiddleError, self.storage.remove_action, self.action_idl_1)

    def test_remove_action__metaaction(self):
        bundle = BundlePrototype.create()

        meta_action_battle = MetaActionArenaPvP1x1Prototype.create(self.storage, self.hero_1, self.hero_2, bundle=bundle)

        proxy_action_1 = actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_1, _bundle_id=bundle.id, meta_action=meta_action_battle)
        proxy_action_2 = actions_prototypes.ActionMetaProxyPrototype.create(hero=self.hero_2, _bundle_id=bundle.id, meta_action=meta_action_battle)

        self.assertEqual(len(self.storage.meta_actions), 1)
        self.assertEqual(len(self.storage.meta_actions_to_actions), 1)
        self.assertEqual(self.storage.meta_actions_to_actions[meta_action_battle.id], set([LogicStorage.get_action_uid(proxy_action_1),
                                                                                           LogicStorage.get_action_uid(proxy_action_2)]))

        self.storage.remove_action(proxy_action_2)

        self.assertEqual(len(self.storage.meta_actions), 1)
        self.assertEqual(len(self.storage.meta_actions_to_actions), 1)
        self.assertEqual(self.storage.meta_actions_to_actions[meta_action_battle.id], set([LogicStorage.get_action_uid(proxy_action_1)]))

        self.storage.remove_action(proxy_action_1)

        self.assertEqual(len(self.storage.meta_actions), 0)
        self.assertEqual(len(self.storage.meta_actions_to_actions), 0)

    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    @mock.patch('the_tale.game.conf.game_settings.SAVED_UNCACHED_HEROES_FRACTION', 0)
    def test_get_bundles_to_save(self):
        # hero 1 not saved
        # hero 2 saved by quota
        # hero 3 saved by caching
        # hero 4 not saved

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')
        result, account_4_id, bundle_4_id = register_user('test_user_4', 'test_user_4@test.com', '111111')
        result, account_5_id, bundle_5_id = register_user('test_user_5', 'test_user_5@test.com', '111111')

        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_4_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_5_id))

        hero_3 = self.storage.accounts_to_heroes[account_3_id]
        hero_4 = self.storage.accounts_to_heroes[account_4_id]

        self.hero_1._model.saved_at = datetime.datetime.now()
        self.hero_1.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        hero_4.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        self.assertTrue(self.hero_1.saved_at > self.hero_2.saved_at)

        self.assertFalse(self.hero_1.is_ui_caching_required)
        self.assertFalse(self.hero_2.is_ui_caching_required)
        self.assertTrue(hero_3.is_ui_caching_required)
        self.assertFalse(hero_4.is_ui_caching_required)

        self.assertEqual(self.storage._get_bundles_to_save(), set([self.bundle_2_id, bundle_3_id, bundle_5_id]))


    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    @mock.patch('the_tale.game.conf.game_settings.SAVED_UNCACHED_HEROES_FRACTION', 0)
    def test_get_bundles_to_save__force_save_required(self):
        # hero 1 not saved
        # hero 2 saved by quota
        # hero 3 saved by caching
        # hero 4 saved by force

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')
        result, account_4_id, bundle_4_id = register_user('test_user_4', 'test_user_4@test.com', '111111')
        result, account_5_id, bundle_5_id = register_user('test_user_5', 'test_user_5@test.com', '111111')

        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_4_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_5_id))

        hero_3 = self.storage.accounts_to_heroes[account_3_id]
        hero_4 = self.storage.accounts_to_heroes[account_4_id]

        hero_4.force_save_required = True

        self.hero_1._model.saved_at = datetime.datetime.now()
        self.hero_1.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        hero_4.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        self.assertTrue(self.hero_1.saved_at > self.hero_2.saved_at)

        self.assertFalse(self.hero_1.is_ui_caching_required)
        self.assertFalse(self.hero_2.is_ui_caching_required)
        self.assertTrue(hero_3.is_ui_caching_required)
        self.assertFalse(hero_4.is_ui_caching_required)

        self.assertEqual(self.storage._get_bundles_to_save(), set([self.bundle_2_id, bundle_3_id, bundle_4_id, bundle_5_id]))

        self.assertFalse(hero_4.force_save_required)


    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', False)
    @mock.patch('the_tale.game.conf.game_settings.SAVED_UNCACHED_HEROES_FRACTION', 0)
    def test_get_bundles_to_save__without_cache_dump(self):
        # hero 1 not saved
        # hero 2 saved by quota
        # hero 3 does not saved by caching
        # hero 4 not saved

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')
        result, account_4_id, bundle_4_id = register_user('test_user_4', 'test_user_4@test.com', '111111')

        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))
        self.storage.load_account_data(AccountPrototype.get_by_id(account_4_id))

        hero_3 = self.storage.accounts_to_heroes[account_3_id]
        hero_4 = self.storage.accounts_to_heroes[account_4_id]

        self.hero_1._model.saved_at = datetime.datetime.now()
        self.hero_1.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        hero_4.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        self.assertTrue(self.hero_1.saved_at > self.hero_2.saved_at)

        self.assertFalse(self.hero_1.is_ui_caching_required)
        self.assertFalse(self.hero_2.is_ui_caching_required)
        self.assertTrue(hero_3.is_ui_caching_required)
        self.assertFalse(hero_4.is_ui_caching_required)

        self.assertEqual(self.storage._get_bundles_to_save(), set([self.bundle_2_id]))

    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', True)
    @mock.patch('the_tale.game.conf.game_settings.SAVED_UNCACHED_HEROES_FRACTION', 0)
    def test_save_changed_data__with_multiple_heroes_to_bundle(self):
        # hero 1 saved by bundle from hero 3
        # hero 2 saved by quota
        # hero 3 saved by caching

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')

        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))

        hero_3 = self.storage.accounts_to_heroes[account_3_id]

        self.hero_1._model.saved_at = datetime.datetime.now()
        self.hero_1.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        self.hero_1.actions.current_action.bundle_id = hero_3.actions.current_action.bundle_id
        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        self.assertTrue(self.hero_1.saved_at > self.hero_2.saved_at)
        self.assertFalse(self.hero_1.is_ui_caching_required)
        self.assertFalse(self.hero_2.is_ui_caching_required)
        self.assertTrue(hero_3.is_ui_caching_required)

        self.assertEqual(self.storage._get_bundles_to_save(), set([self.bundle_2_id, bundle_3_id]))

        self.storage.process_turn()

        with mock.patch('dext.common.utils.cache.set_many') as set_many:
            with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
                with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                    self.storage.save_changed_data()

        self.assertEqual(set_many.call_count, 1)
        self.assertEqual(save_hero_data.call_count, 3)
        self.assertEqual(ui_info.call_count, 2)
        self.assertEqual(ui_info.call_args_list, [mock.call(actual_guaranteed=True), mock.call(actual_guaranteed=True)])


    @mock.patch('the_tale.game.heroes.conf.heroes_settings.DUMP_CACHED_HEROES', False)
    @mock.patch('the_tale.game.conf.game_settings.SAVED_UNCACHED_HEROES_FRACTION', 0)
    def test_save_changed_data__with_multiple_heroes_to_bundle__without_cache_dump(self):
        # hero 1 saved by bundle from hero 2
        # hero 2 saved by quota
        # hero 3 does not saved by caching

        result, account_3_id, bundle_3_id = register_user('test_user_3', 'test_user_3@test.com', '111111')

        self.storage.load_account_data(AccountPrototype.get_by_id(account_3_id))

        hero_3 = self.storage.accounts_to_heroes[account_3_id]

        self.hero_1._model.saved_at = datetime.datetime.now()
        self.hero_1.ui_caching_started_at = datetime.datetime.fromtimestamp(0)
        self.hero_1.actions.current_action.bundle_id = self.hero_2.actions.current_action.bundle_id
        self.hero_2.ui_caching_started_at = datetime.datetime.fromtimestamp(0)

        self.assertTrue(self.hero_1.saved_at > self.hero_2.saved_at)
        self.assertFalse(self.hero_1.is_ui_caching_required)
        self.assertFalse(self.hero_2.is_ui_caching_required)
        self.assertTrue(hero_3.is_ui_caching_required)

        self.assertEqual(self.storage._get_bundles_to_save(), set([self.bundle_2_id]))

        self.storage.process_turn()

        with mock.patch('dext.common.utils.cache.set_many') as set_many:
            with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as save_hero_data:
                with mock.patch('the_tale.game.heroes.prototypes.HeroPrototype.ui_info') as ui_info:
                    self.storage.save_changed_data()

        self.assertEqual(set_many.call_count, 1)
        self.assertEqual(save_hero_data.call_count, 2)
        self.assertEqual(ui_info.call_count, 1)
        self.assertEqual(ui_info.call_args, mock.call(actual_guaranteed=True))


    def test_merge_bundles(self):

        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3])

        storage.merge_bundles([555, 666], 777)

        self.assertEqual(storage.bundles_to_accounts, {777: set([1, 2, 3])})


    def test_merge_bundles__in_existed_bundle(self):

        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3])
        storage.bundles_to_accounts[777] = set([4, 5])

        storage.merge_bundles([555, 666], 777)

        self.assertEqual(storage.bundles_to_accounts, {777: set([1, 2, 3, 4, 5])})

    def test_unmerge_bundles__in_existed_bundle(self):
        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3])
        storage.bundles_to_accounts[777] = set([4, 5])

        storage.unmerge_bundles(4, 777, 666)

        self.assertEqual(storage.bundles_to_accounts, {555: set([1, 2]),
                                                       666: set([3, 4]),
                                                       777: set([5])})

    def test_unmerge_bundles__last_account_in_bundle(self):
        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3])
        storage.bundles_to_accounts[777] = set([4, 5])

        storage.unmerge_bundles(3, 666, 555)

        self.assertEqual(storage.bundles_to_accounts, {555: set([1, 2, 3]),
                                                       777: set([4, 5])})

    def test_unmerge_bundles(self):
        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3])
        storage.bundles_to_accounts[777] = set([4, 5])

        storage.unmerge_bundles(4, 777, 888)

        self.assertEqual(storage.bundles_to_accounts, {555: set([1, 2]),
                                                       666: set([3]),
                                                       777: set([5]),
                                                       888: set([4])})


    def test_save_bundle_data(self):

        storage = LogicStorage()

        storage.bundles_to_accounts[555] = set([1, 2])
        storage.bundles_to_accounts[666] = set([3, 7, 9])
        storage.bundles_to_accounts[777] = set([4, 5])

        storage.accounts_to_heroes = {1: mock.Mock(id=1),
                                      2: mock.Mock(id=2),
                                      3: mock.Mock(id=3),
                                      4: mock.Mock(id=4),
                                      5: mock.Mock(id=5),
                                      7: mock.Mock(id=7),
                                      9: mock.Mock(id=9)}

        with mock.patch('the_tale.game.logic_storage.LogicStorage._save_hero_data') as _save_hero_data:
            storage.save_bundle_data(666, update_cache=True)

        self.assertEqual(_save_hero_data.call_count, 3)

        self.assertTrue(all(call[1]['update_cache'] for call in _save_hero_data.call_args_list))
        self.assertEqual(set(call[0][0] for call in _save_hero_data.call_args_list), set([3, 7, 9]))
