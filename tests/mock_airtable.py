"""A mocked Airtable API wrapper."""
from unittest import mock
from requests.exceptions import HTTPError

def get_mock_airtable():
    """
    Wrap it in a function, so it's pure
    """

    class MockTable(mock.Mock):
        def iterate(self):
            return [self.all()]


    MockTable.table_name = "app_airtable_advert_base_key"

    MockTable.get = mock.MagicMock("get")

    def get_fn(record_id):
        if record_id == "recNewRecordId":
            return {
                "id": "recNewRecordId",
                "fields": {
                    "title": "Red! It's the new blue!",
                    "description": "Red is a scientifically proven color that moves faster than all other colors.",
                    "external_link": "https://example.com/",
                    "is_active": True,
                    "rating": "1.5",
                    "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
                    "points": 95,
                    "slug": "red-its-new-blue",
                },
            }
        else:
            raise HTTPError("404 Client Error: Not Found")

    MockTable.get.side_effect = get_fn

    MockTable.create = mock.MagicMock("create")

    MockTable.create.return_value = {
        "id": "recNewRecordId",
        "fields": {
            "title": "Red! It's the new blue!",
            "description": "Red is a scientifically proven color that moves faster than all other colors.",
            "external_link": "https://example.com/",
            "is_active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
        },
    }

    MockTable.update = mock.MagicMock("update")
    MockTable.update.return_value = {
        "id": "recNewRecordId",
        "fields": {
            "title": "Red! It's the new blue!",
            "description": "Red is a scientifically proven color that moves faster than all other colors.",
            "external_link": "https://example.com/",
            "is_active": True,
            "rating": "1.5",
            "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
            "points": 95,
            "slug": "red-its-new-blue",
        },
    }

    MockTable.delete = mock.MagicMock("delete")
    MockTable.delete.return_value = {"deleted": True, "record": "recNewRecordId"}

    MockTable.search = mock.MagicMock("search")
    def search_fn(field, value):
        if field == "slug" and value == "red-its-new-blue":
            return [
                {
                    "id": "recNewRecordId",
                    "fields": {
                        "title": "Red! It's the new blue!",
                        "description": "Red is a scientifically proven color that moves faster than all other colors.",
                        "external_link": "https://example.com/",
                        "is_active": True,
                        "rating": "1.5",
                        "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
                        "points": 95,
                        "slug": "red-its-new-blue",
                    },
                },
                {
                    "id": "Different record",
                    "fields": {
                        "title": "Not the used record.",
                        "description": "This is only used for multiple responses from MockAirtable",
                        "external_link": "https://example.com/",
                        "is_active": False,
                        "rating": "5.5",
                        "long_description": "",
                        "points": 1,
                        "slug": "not-the-used-record",
                    },
                },
            ]
        elif field == "slug" and value == "a-matching-slug":
            return [
                {
                    "id": "recMatchedRecordId",
                    "fields": {
                        "title": "Red! It's the new blue!",
                        "description": "Red is a scientifically proven color that moves faster than all other colors.",
                        "external_link": "https://example.com/",
                        "is_active": True,
                        "rating": "1.5",
                        "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
                        "points": 95,
                        "slug": "a-matching-slug",
                    },
                },
            ]
        elif field == "Page Slug" and value == "home":
            return [
                {
                    "id": "recHomePageId",
                    "fields": {
                        "title": "Home",
                        "Page Slug": "home",
                        "intro": "This is the home page.",
                    },
                },
            ]
        else:
            return []

    MockTable.search.side_effect = search_fn

    MockTable.all = mock.MagicMock("all")
    MockTable.all.return_value = [
        {
            "id": "recNewRecordId",
            "fields": {
                "title": "Red! It's the new blue!",
                "description": "Red is a scientifically proven color that moves faster than all other colors.",
                "external_link": "https://example.com/",
                "is_active": True,
                "rating": "1.5",
                "long_description": "<p>Lorem ipsum dolor sit amet, consectetur adipisicing elit. Veniam laboriosam consequatur saepe. Repellat itaque dolores neque, impedit reprehenderit eum culpa voluptates harum sapiente nesciunt ratione.</p>",
                "points": 95,
                "slug": "delete-me",
                "publications": [
                    {"title": "Record 1 publication 1"},
                    {"title": "Record 1 publication 2"},
                    {"title": "Record 1 publication 3"},
                ]
            },
        },
        {
            "id": "Different record",
            "fields": {
                "title": "Not the used record.",
                "description": "This is only used for multiple responses from MockAirtable",
                "external_link": "https://example.com/",
                "is_active": False,
                "rating": "5.5",
                "long_description": "",
                "points": 1,
                "slug": "not-the-used-record",
            },
        },
        {
            "id": "recRecordThree",
            "fields": {
                "title": "A third record.",
                "description": "This is only used for multiple responses from MockAirtable",
                "external_link": "https://example.com/",
                "is_active": False,
                "rating": "5.5",
                "long_description": "",
                "points": 1,
                "slug": "record-3",
            },
        },
        {
            "id": "recRecordFour",
            "fields": {
                "title": "A fourth record.",
                "description": "This is only used for multiple responses from MockAirtable",
                "external_link": "https://example.com/",
                "is_active": False,
                "rating": "5.5",
                "long_description": "",
                "points": 1,
                "slug": "record-4",
                "publications": [
                    {"title": "Record 4 publication 1"},
                    {"title": "Record 4 publication 2"},
                    {"title": "Record 4 publication 3"},
                ]
            },
        },
    ]

    class MockApi(mock.Mock):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._table = MockTable()

        def table(self, base_id, table_name):
            return self._table

    return MockApi