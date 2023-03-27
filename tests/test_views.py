from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from tests.models import Advert


class TestAdminViews(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test_get(self):
        response = self.client.get(reverse('airtable_import_listing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Models you can import from Airtable')
        self.assertContains(response, 'Advert')
        self.assertNotContains(response, 'Simple Page')

    def test_list_snippets(self):
        url = reverse('wagtailsnippets_tests_advert:list')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_snippet_detail(self):
        url = reverse('wagtailsnippets_tests_advert:edit', args=[1])

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Ensure the default Advert does not have an Airtable Record ID
        instance = response.context_data['object']

        self.assertEqual(instance.airtable_record_id, '')

    def test_import_snippet_button_on_list_view(self):
        url = reverse('wagtailsnippets_tests_advert:list')

        response = self.client.get(url)
        self.assertContains(response, 'Import Advert')

    def test_no_import_snippet_button_on_list_view(self):
        url = reverse('wagtailsnippets_tests_modelnotused:list')

        response = self.client.get(url)
        self.assertNotContains(response, 'Import Advert')

    def test_airtable_message_on_instance_create(self):
        url = reverse('wagtailsnippets_tests_advert:add')

        response = self.client.post(url, {
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

        url = reverse('wagtailsnippets_tests_advert:edit', args=[advert.pk])

        response = self.client.post(url, {
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

        url = reverse('wagtailsnippets_tests_advert:delete', args=[advert.pk])

        response = self.client.post(url)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 2)
        self.assertIn('Advertisement &#x27;Wow brand new?!&#x27; deleted', messages[0].message)
        self.assertIn('Airtable record deleted', messages[1].message)
