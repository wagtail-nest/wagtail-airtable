from django.test import TestCase


class TestAdminViews(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test_get(self):
        response = self.client.get('/admin/airtable-import/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Models you can import from Airtable')
        self.assertContains(response, 'Simple Page')
        self.assertContains(response, 'Advert')

    def test_list_snippets(self):
        response = self.client.get('/admin/snippets/tests/advert/')
        self.assertEqual(response.status_code, 200)

    def test_snippet_detail(self):
        response = self.client.get('/admin/snippets/tests/advert/1/')
        self.assertEqual(response.status_code, 200)
        # Ensure the default Advert does not have an Airtable Record ID
        instance = response.context_data['instance']
        self.assertEqual(instance.airtable_record_id, '')

