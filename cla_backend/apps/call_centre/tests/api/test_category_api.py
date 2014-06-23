from rest_framework.test import APITestCase

from core.tests.test_base import CLAOperatorAuthBaseApiTestMixin

from legalaid.tests.views.category_api import CategoryAPIMixin


class CategoryTestCase(CategoryAPIMixin, CLAOperatorAuthBaseApiTestMixin, APITestCase):
    def get_http_authorization(self):
        return 'Bearer %s' % self.token
