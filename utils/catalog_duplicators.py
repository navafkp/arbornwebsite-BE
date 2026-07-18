from django.utils.crypto import get_random_string

from catalog.models import ProductTag


class CatalogDuplicator:
    """Knows how to create duplicates of catalog objects."""

    def duplicate_product(self, product):
        variants = list(product.variants.all())
        tag_links = list(ProductTag.objects.filter(product=product))

        product.pk = None
        product.id = None
        product.name = f"{product.name}-copy-{get_random_string(6).lower()}"
        product.slug = f"{product.slug}-copy-{get_random_string(6).lower()}"
        product.save()

        for tag_link in tag_links:
            ProductTag.objects.create(product=product, tag=tag_link.tag)

        for variant in variants:
            images = list(variant.images.all())
            size_stocks = list(variant.size_stocks.all())
            variant.pk = None
            variant.id = None
            variant.product = product
            variant.save()
            for image in images:
                image.pk = None
                image.id = None
                image.variant = variant
                image.save()
            for stock in size_stocks:
                stock.pk = None
                stock.id = None
                stock.variant = variant
                stock.sku = ""
                stock.save()

        return product

    def duplicate_variant(self, variant):
        images = list(variant.images.all())
        size_stocks = list(variant.size_stocks.all())
        variant.pk = None
        variant.id = None
        variant.color = f"{variant.color}-copy-{get_random_string(6).lower()}"
        variant.save()

        for image in images:
            image.pk = None
            image.id = None
            image.variant = variant
            image.save()

        for stock in size_stocks:
            stock.pk = None
            stock.id = None
            stock.variant = variant
            stock.sku = ""
            stock.save()

        return variant

    def duplicate_tag(self, tag):
        tag.pk = None
        tag.id = None
        tag.name = f"{tag.name}-copy-{get_random_string(6).lower()}"
        tag.slug = f"{tag.slug}-copy-{get_random_string(6).lower()}"
        tag.save()
        return tag


catalog_duplicator = CatalogDuplicator()
