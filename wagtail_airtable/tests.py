"""A mocked Airtable API wrapper."""
from unittest import mock


class MockAirtable(mock.Mock):
    pass


MockAirtable.table_name = "app_airtable_advert_base_key"

MockAirtable.get = mock.MagicMock("get")
MockAirtable.get.return_value = {
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
MockAirtable.search.return_value = [
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
        },
    },
]
