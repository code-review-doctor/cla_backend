from rest_framework import status

from core.tests.mommy_utils import make_recipe
from core.tests.test_base import \
    NestedSimpleResourceAPIMixin


class CaseNotesHistoryAPIMixin(NestedSimpleResourceAPIMixin):
    LOOKUP_KEY = 'reference'
    API_URL_BASE_NAME = 'notes_history'
    RESOURCE_RECIPE = 'legalaid.notes_history'
    LOOKUP_KEY = 'case_reference'
    PARENT_LOOKUP_KEY = 'reference'
    PARENT_RESOURCE_RECIPE = 'legalaid.case'
    PK_FIELD = 'case'
    ONE_TO_ONE_RESOURCE = False

    def setup_resources(self):
        super(CaseNotesHistoryAPIMixin, self).setup_resources()
        self.operator_notes = make_recipe(
            self.RESOURCE_RECIPE, case=self.parent_resource,
            operator_notes='Operator notes',
            provider_notes=None,
            _quantity=4
        )
        self.minor_logs = make_recipe(
            self.RESOURCE_RECIPE, case=self.parent_resource,
            provider_notes='Provider notes',
            operator_notes=None,
            _quantity=4
        )

    def make_resource(self, **kwargs):
        return None

    def test_methods_not_allowed(self):
        """
        Ensure that we can't POST, PUT or DELETE
        """
        self._test_post_not_allowed(self.list_url)
        self._test_put_not_allowed(self.list_url)
        self._test_delete_not_allowed(self.list_url)

    def test_methods_not_authorized(self):
        self._test_get_not_authorized(self.list_url, self.invalid_token)

    def test_get_without_type_param(self):
        response = self.client.get(
            self.list_url, HTTP_AUTHORIZATION=self.get_http_authorization()
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        import pdb; pdb.set_trace()
        # self.assertItemsEqual(
        #     [log.code for log in self.high_logs],
        #     [log['code'] for log in response.data]
        # )
