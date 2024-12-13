"""A mocked Airtable API wrapper."""
from unittest import mock
from requests.exceptions import HTTPError

def get_mock_airtable():
    """
    Wrap it in a function, so it's pure
    """

    class MockAirtable(mock.Mock):
        def get_iter(self):
            return [self.get_all()]


    MockAirtable.table_name = "app_airtable_advert_base_key"

    MockAirtable.get = mock.MagicMock("get")

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

    MockAirtable.get.side_effect = get_fn

    MockAirtable.insert = mock.MagicMock("insert")

    MockAirtable.insert.return_value = {
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

    MockAirtable.update = mock.MagicMock("update")
    MockAirtable.update.return_value = {
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

    MockAirtable.delete = mock.MagicMock("delete")
    MockAirtable.delete.return_value = {"deleted": True, "record": "recNewRecordId"}

    MockAirtable.search = mock.MagicMock("search")
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

    MockAirtable.search.side_effect = search_fn

    MockAirtable.get_all = mock.MagicMock("get_all")
    MockAirtable.get_all.return_value = [
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

    return MockAirtable