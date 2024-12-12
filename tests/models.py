from django.db import models
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import IndexView, SnippetViewSet

from wagtail_airtable.mixins import AirtableMixin, SnippetImportActionMixin


class SimplePage(Page):
    intro = models.TextField()


class Publication(models.Model):
    title = models.CharField(max_length=30)


class Advert(AirtableMixin, models.Model):
    STAR_RATINGS = (
        (1.0, "1"),
        (1.5, "1.5"),
        (2.0, "2"),
        (2.5, "2.5"),
        (3.0, "3"),
        (3.5, "3.5"),
        (4.0, "4"),
        (4.5, "4.5"),
        (5.0, "5"),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    external_link = models.URLField(blank=True, max_length=500)
    is_active = models.BooleanField(default=False)
    rating = models.DecimalField(
        null=True, choices=STAR_RATINGS, decimal_places=1, max_digits=2
    )
    long_description = RichTextField(blank=True, null=True)
    points = models.IntegerField(null=True, blank=True)
    slug = models.SlugField(max_length=100, unique=True, editable=True)
    publications = models.ManyToManyField(Publication, blank=True)

    @classmethod
    def map_import_fields(cls):
        """{'Airtable column name': 'model_field_name', ...}"""
        mappings = {
            "title": "title",
            "description": "description",
            "external_link": "external_link",
            "is_active": "is_active",
            "rating": "rating",
            "long_description": "long_description",
            "points": "points",
            "slug": "slug",
            "publications": "publications",
        }
        return mappings

    def get_export_fields(self):
        return {
            "title": self.title,
            "description": self.description,
            "external_link": self.external_link,
            "is_active": self.is_active,
            "rating": self.rating,
            "long_description": self.long_description,
            "points": self.points,
            "slug": self.slug,
            "publications": self.publications,
        }

    class Meta:
        verbose_name = "Advertisement"
        verbose_name_plural = "Advertisements"

    def __str__(self):
        return self.title


class AdvertIndexView(SnippetImportActionMixin, IndexView):
    pass


class AdvertViewSet(SnippetViewSet):
    model = Advert
    index_view_class = AdvertIndexView

register_snippet(Advert, viewset=AdvertViewSet)


@register_snippet
class SimilarToAdvert(Advert):
    pass


@register_snippet
class ModelNotUsed(AirtableMixin, models.Model):
    pass
