# coding: utf-8

from textgen.words import Noun

from dext.forms import fields

from game.game_info import GENDER

from game.balance.enums import RACE

from game.persons.relations import PERSON_TYPE
from game.persons.prototypes import PersonPrototype

from game.bills.relations import BILL_TYPE
from game.bills.forms import BaseUserForm, BaseModeratorForm

from game.persons.storage import persons_storage


class UserForm(BaseUserForm):

    person = fields.ChoiceField(label=u'Персонаж')

    def __init__(self, choosen_person_id, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['person'].choices = PersonPrototype.form_choices(only_weak=True, choosen_person=persons_storage[choosen_person_id])


class ModeratorForm(BaseModeratorForm):
    pass

class PersonRemove(object):

    type = BILL_TYPE.PERSON_REMOVE

    UserForm = UserForm
    ModeratorForm = ModeratorForm

    USER_FORM_TEMPLATE = 'bills/bills/person_remove_user_form.html'
    MODERATOR_FORM_TEMPLATE = 'bills/bills/person_remove_moderator_form.html'
    SHOW_TEMPLATE = 'bills/bills/person_remove_show.html'

    CAPTION = u'Закон об изгнании персонажа'
    DESCRIPTION = u'В случае если персонаж утратил доверие духов-хранителей, его можно изгнать из города. Изгонять можно только наименее влиятельных персонажей.'

    def __init__(self, person_id=None, old_place_name_forms=None):
        self.old_place_name_forms = old_place_name_forms
        self.person_id = person_id

        if person_id is not None:
            self.person_name = self.person.name
            self.person_race = self.person.race
            self.person_type = self.person.type
            self.person_gender = self.person.gender

    @property
    def person(self):
        return persons_storage[self.person_id]

    @property
    def old_place_name(self):
        return self.old_place_name_forms.normalized

    @property
    def person_race_verbose(self):
        return RACE._ID_TO_TEXT[self.person_race]

    @property
    def person_gender_verbose(self):
        return GENDER._ID_TO_TEXT[self.person_gender]

    @property
    def user_form_initials(self):
        return {'person': self.person_id}

    @property
    def moderator_form_initials(self):
        return {}

    def initialize_with_user_data(self, user_form):
        self.person_id = int(user_form.c.person)
        self.old_place_name_forms = self.person.place.normalized_name

        self.person_name = self.person.name
        self.person_race = self.person.race
        self.person_type = self.person.type
        self.person_gender = self.person.gender


    def initialize_with_moderator_data(self, moderator_form):
        pass

    @classmethod
    def get_user_form_create(cls, post=None):
        return UserForm(None, post)

    def get_user_form_update(self, post=None, initial=None):
        if initial:
            return UserForm(self.person_id, initial=initial)
        return  UserForm(self.person_id, post)

    def apply(self):
        self.person.move_out_game()
        self.person.place.sync_persons()
        self.person.save()


    def serialize(self):
        return {'type': self.type.name.lower(),
                'person_id': self.person_id,
                'person_name': self.person_name,
                'person_race': self.person_race,
                'person_type': self.person_type.value,
                'person_gender': self.person_gender,
                'old_place_name_forms': self.old_place_name_forms.serialize()}

    @classmethod
    def deserialize(cls, data):
        obj = cls()
        obj.person_id = data['person_id']
        obj.person_name = data['person_name']
        obj.person_race = data['person_race']
        obj.person_type = PERSON_TYPE(data['person_type'])
        obj.person_gender = data['person_gender']

        if 'old_name_forms' in data:
            obj.old_place_name_forms = Noun.deserialize(data['old_place_name_forms'])
        else:
            obj.old_place_name_forms = Noun.fast_construct(u'название неизвестно')


        return obj
