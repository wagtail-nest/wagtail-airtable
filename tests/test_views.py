from django.contrib.messages import get_messages
from django.test import TestCase

from tests.models import Advert
from unittest.mock import patch
from wagtail_airtable.tests import get_mock_airtable


class TestAdminViews(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        airtable_patcher = patch("wagtail_airtable.mixins.Airtable", new_callable=get_mock_airtable())
        airtable_patcher.start()
        self.addCleanup(airtable_patcher.stop)

        self.client.login(username='admin', password='password')

    def test_get(self):
        response = self.client.get('/admin/airtable-import/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Models you can import from Airtable')
        self.assertContains(response, 'Advert')
        self.assertNotContains(response, 'Simple Page')

    def test_list_snippets(self):
        response = self.client.get('/admin/snippets/tests/advert/')
        self.assertEqual(response.status_code, 200)

    def test_snippet_detail(self):
        response = self.client.get('/admin/snippets/tests/advert/1/')
        self.assertEqual(response.status_code, 200)
        # Ensure the default Advert does not have an Airtable Record ID
        instance = response.context_data['instance']
        self.assertEqual(instance.airtable_record_id, '')

    def test_import_snippet_button_on_list_view(self):
        response = self.client.get('/admin/snippets/tests/advert/')
        self.assertContains(response, 'Import Advert')

    def test_no_import_snippet_button_on_list_view(self):
        response = self.client.get('/admin/snippets/tests/modelnotused/')
        self.assertNotContains(response, 'Import Advert')

    def test_airtable_message_on_instance_create(self):
        response = self.client.post('/admin/snippets/tests/advert/add/', {
            'title': 'New advert',
            'description': 'Lorem ipsum dolor sit amet, consectetur adipisicing elit.',
            'rating': "1.5",
            'slug': 'wow-super-new-advert',
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertIn('Advertisement &#x27;New advert&#x27; created', messages[0].message)
        self.assertIn('Airtable record updated', messages[1].message)

    def test_airtable_message_on_instance_edit(self):
        advert = Advert.objects.first()
        response = self.client.post(f'/admin/snippets/tests/advert/{advert.id}/', {
            'title': 'Edited',
            'description': 'Edited advert',
            'slug': 'crazy-edited-advert-insane-right',
            'rating': "1.5",
            'is_active': True,
        })
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertIn('Advertisement &#x27;Edited&#x27; updated', messages[0].message)
        self.assertIn('Airtable record updated', messages[1].message)

    def test_airtable_message_on_instance_delete(self):
        advert = Advert.objects.get(slug='delete-me')
        response = self.client.post(f'/admin/snippets/tests/advert/{advert.id}/delete/')
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertIn('Advertisement &#x27;Wow brand new?!&#x27; deleted', messages[0].message)
        self.assertIn('Airtable record deleted', messages[1].message)
