from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from .models import *


class TestOwner(TestCase):

    def test_owner_creation_with_no_user_or_organization_fails(self):
        self.assertRaises(ValidationError, Owner.objects.create)

    def test_owner_creation_with_user_and_organization_both_fails(self):
        user = User.objects.create_user(username='foo')
        org = Organization.create(admin=user, name='Org')
        self.assertRaises(ValidationError, Owner.objects.create, user=user,
            organization=org)

    def test_owner_can_be_created_with_user(self):
        user = User.objects.create_user(username='foo')
        owner = Owner.create_for_user(user)
        self.assertTrue(owner.is_user)

    def test_owner_can_be_created_with_organization(self):
        user = User.objects.create_user(username='foo')
        org = Organization.create(admin=user, name='Org')
        owner = Owner.create_for_organization(org)
        self.assertTrue(owner.is_organization)


class TestItem(TestCase):

    def test_item_creation_sets_owner_and_holder(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        item = Item.create(owner=owner, type='other', name='name')

        self.assertEqual(item.owner, owner)
        self.assertEqual(item.holder, owner)

    def test_give_item_changes_owner(self):
        orig_owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        new_owner = Owner.create_for_user(
            User.objects.create_user(username='bar'))
        item = Item.create(owner=orig_owner, type='other', name='name')

        item.owner = new_owner
        self.assertEqual(item.owner, new_owner)

    def test_lend_item_changes_holder(self):
        orig_holder = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        new_holder = Owner.create_for_user(
            User.objects.create_user(username='bar'))
        item = Item.create(owner=orig_holder, type='other', name='name')

        item.holder = new_holder
        self.assertEqual(item.holder, new_holder)

    def test_owned_item_shows_in_owned_items_list(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        item = Item.create(owner=owner, type='other', name='name')

        self.assertTrue(item in owner.owned_items)

    def test_borrowed_item_shows_in_borrowed_items_list(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        borrower = Owner.create_for_user(
            User.objects.create_user(username='bar'))
        item = Item.create(owner=owner, type='other', name='name')

        item.holder = borrower
        self.assertTrue(item in borrower.borrowed_items)

    def test_lent_item_shows_in_lent_items_list(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        borrower = Owner.create_for_user(
            User.objects.create_user(username='bar'))
        item = Item.create(owner=owner, type='other', name='name')

        item.holder = borrower
        self.assertTrue(item in owner.lent_items)

    def test_returned_item_is_back_at_owner(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        borrower = Owner.create_for_user(
            User.objects.create_user(username='bar'))
        item = Item.create(owner=owner, type='other', name='name')
        item.holder = borrower

        item.return_to_owner()
        self.assertEqual(item.holder, owner)

    def test_returned_item_has_no_owner_borrower(self):
        owner = Owner.create_for_user(
            User.objects.create_user(username='foo'))
        item = Item.create(owner=owner, type='other', name='name')

        item.dispose()
        self.assertEqual(item.owner, None)
        self.assertEqual(item.holder, None)
