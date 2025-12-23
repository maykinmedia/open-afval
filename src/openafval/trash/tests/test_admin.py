from django.urls import reverse

from django_webtest import WebTest
from maykin_2fa.test import disable_admin_mfa

from openafval.accounts.tests.factories import UserFactory
from openafval.trash.tests.factories import (
    BagObjectFactory,
    ContainerFactory,
    ContainerTypeFactory,
    EmptyingFactory,
    EntityFactory,
    EntityObjectManagementFactory,
    FractionFactory,
)


@disable_admin_mfa()
class BagObjectAdminTestCase(WebTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(superuser=True)

    def test_bag_object_list_view(self):
        BagObjectFactory.create_batch(2)
        response = self.app.get(
            reverse("admin:trash_bagobject_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)

    def test_entity_list_view(self):
        EntityFactory.create_batch(2)
        response = self.app.get(
            reverse("admin:trash_entity_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)

    def test_entity_object_management_list_view(self):
        EntityObjectManagementFactory.create_batch(2)
        response = self.app.get(
            reverse("admin:trash_entityobjectmanagement_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)

    def test_container_type_list_view(self):
        faction_1 = FractionFactory.create(
            identifier="test_identifier_1", description="test_description_1"
        )
        faction_2 = FractionFactory.create(
            identifier="test_identifier_2", description="test_description_2"
        )

        ContainerTypeFactory.create(fraction=faction_1)
        ContainerTypeFactory.create(fraction=faction_2)

        response = self.app.get(
            reverse("admin:trash_containertype_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-description", 2)

        # test fk display fraction 1
        self.assertContains(response, "test_identifier_1")
        self.assertContains(response, "test_description_1")

        # test fk display fraction 2
        self.assertContains(response, "test_identifier_2")
        self.assertContains(response, "test_description_2")

    def test_container_list_view(self):
        type_1 = ContainerTypeFactory.create(
            type="test_type_1", description="test_description_1"
        )
        type_2 = ContainerTypeFactory.create(
            type="test_type_2", description="test_description_2"
        )

        ContainerFactory.create(type=type_1)
        ContainerFactory.create(type=type_2)

        response = self.app.get(
            reverse("admin:trash_container_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)

        # test fk display fraction 1
        self.assertContains(response, "test_type_1")
        self.assertContains(response, "test_description_1")

        # test fk display fraction 2
        self.assertContains(response, "test_type_2")
        self.assertContains(response, "test_description_2")

    def test_emptying_list_view(self):
        EmptyingFactory.create_batch(2)
        response = self.app.get(
            reverse("admin:trash_emptying_changelist"),
            user=self.user,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "field-identifier", 2)
