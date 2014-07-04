from cla_eventlog import event_registry
from django.contrib.auth.models import AnonymousUser

from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action, link
from rest_framework.response import Response as DRFResponse
from rest_framework.filters import OrderingFilter, SearchFilter, \
    DjangoFilterBackend

from cla_common.constants import CASE_STATES
from cla_provider.models import Provider, OutOfHoursRota
from cla_provider.helpers import ProviderAllocationHelper
from cla_eventlog.views import BaseEventViewSet
from timer.views import BaseTimerViewSet
from legalaid.models import Case, PersonalDetails, ThirdPartyDetails, \
    AdaptationDetails
from legalaid.views import BaseUserViewSet, StateFromActionMixin, \
    BaseCategoryViewSet, BaseEligibilityCheckViewSet
from knowledgebase.views import BaseArticleViewSet, BaseArticleCategoryViewSet

from timer.utils import get_or_create_timer

from .permissions import CallCentreClientIDPermission, \
    OperatorManagerPermission
from .serializers import EligibilityCheckSerializer, \
    CaseSerializer, ProviderSerializer,  \
    OutOfHoursRotaSerializer, OperatorSerializer, PersonalDetailsSerializer, \
    ThirdPartyDetailsSerializer, AdaptationDetailsSerializer

from .forms import ProviderAllocationForm,  DeclineAllSpecialistsCaseForm,\
    AssociatePersonalDetailsCaseForm, AssociateThirdPartyDetailsCaseForm,\
    AssociateAdaptationDetailsCaseForm, AssociateEligibilityCheckCaseForm, \
    DeferAssignmentCaseForm

from .models import Operator


class CallCentrePermissionsViewSetMixin(object):
    permission_classes = (CallCentreClientIDPermission,)


class CallCentreManagerPermissionsViewSetMixin(object):
    permission_classes = (
        CallCentreClientIDPermission, OperatorManagerPermission)


class CategoryViewSet(CallCentrePermissionsViewSetMixin, BaseCategoryViewSet):
    pass


class EligibilityCheckViewSet(
    CallCentrePermissionsViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    BaseEligibilityCheckViewSet
):
    serializer_class = EligibilityCheckSerializer

    @link()
    def validate(self, request, **kwargs):
        obj = self.get_object()
        return DRFResponse(obj.validate())

    def pre_save(self, obj):
        user = self.request.user
        means_test_event = event_registry.get_event('means_test')()
        diff = obj.diff
        diff.pop('id', None)
        try:

            means_test_event.process(obj.case,
                                     notes="",
                                     created_by=user,
                                     status='changed'
                                     )
        except:
            pass

        return super(EligibilityCheckViewSet, self).pre_save(obj)


class CaseViewSet(
    CallCentrePermissionsViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    StateFromActionMixin,
    viewsets.GenericViewSet
):
    model = Case
    lookup_field = 'reference'
    serializer_class = CaseSerializer

    filter_backends = (
        OrderingFilter,
        SearchFilter,
    )

    ordering_fields = ('modified', 'created')
    ordering = '-modified'

    search_fields = ('personal_details__full_name',
                     'personal_details__postcode',
                     'reference',
                     'laa_reference')
    paginate_by = 20
    paginate_by_param = 'page_size'
    max_paginate_by = 100

    # NOTE commented out because it may make more sense to get_or_create_timer
    #   when creating a Log object instead
    # def get_object(self, queryset=None):
    #     """
    #     TODO: we might need to override retrieve instead so that we don't
    #         hit the db during POST, PATCH etc.
    #     """
    #     obj = super(CaseViewSet, self).get_object(queryset=queryset)
    #     get_or_create_timer(self.request.user)
    #     return obj

    def get_queryset(self):
        qs = super(CaseViewSet, self).get_queryset()
        dashboard_param = self.request.QUERY_PARAMS.get('dashboard', None)
        if dashboard_param:
            qs = qs.filter(state=CASE_STATES.OPEN, provider=None)
        return qs

    def pre_save(self, obj, *args, **kwargs):
        super(CaseViewSet, self).pre_save(obj, *args, **kwargs)

        user = self.request.user
        if not obj.pk and not isinstance(user, AnonymousUser):
            obj.created_by = user

    @link()
    def assign_suggest(self, request, reference=None, **kwargs):
        """
        @return: dict - 'suggested_provider' (single item) ;
                        'suitable_providers' all possible providers for this category.
        """
        obj = self.get_object()
        helper = ProviderAllocationHelper()

        if hasattr(obj, 'eligibility_check') and obj.eligibility_check != None and obj.eligibility_check.category:
            category = obj.eligibility_check.category
            suggested = helper.get_suggested_provider(category)

            if suggested:
                suggested_provider = ProviderSerializer(suggested).data
            else:
                suggested_provider = None
        else:
            category = None
            suggested_provider = None

        suitable_providers = [
            ProviderSerializer(p).data for p in helper.get_qualifying_providers(category)]
        suggestions = {'suggested_provider': suggested_provider,
                       'suitable_providers': suitable_providers
                       }

        return DRFResponse(suggestions)

    @action()
    def assign(self, request, reference=None, **kwargs):
        """
        Assigns the case to a provider
        """
        obj = self.get_object()
        helper = ProviderAllocationHelper()

        category = obj.eligibility_check.category if obj.eligibility_check else None
        suitable_providers = helper.get_qualifying_providers(category)

        # find given provider in suitable - avoid extra lookup and ensures
        # valid provider
        for sp in suitable_providers:
            if sp.id == int(request.DATA['provider_id']):
                p = sp
                break
        else:
            raise ValueError("Provider not found")

        # if we're inside office hours then:
        # Randomly assign to provider who offers this category of service
        # else it should be the on duty provider
        data = request.DATA.copy()
        data['provider'] = p.pk
        form = ProviderAllocationForm(case=obj,
                                      data=data,
                                      providers=suitable_providers)

        if form.is_valid():
            provider = form.save(request.user)
            provider_serialised = ProviderSerializer(provider)
            return DRFResponse(data=provider_serialised.data)

        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )

    @action()
    def defer_assignment(self, request, **kwargs):
        obj = self.get_object()
        form = DeferAssignmentCaseForm(case=obj, data=request.DATA)
        if form.is_valid():
            form.save(request.user)
            return DRFResponse(status=status.HTTP_204_NO_CONTENT)

        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )

    @action()
    def decline_all_specialists(self, request, reference=None, **kwargs):
        return self._state_form_action(request, DeclineAllSpecialistsCaseForm)

    @action()
    def associate_personal_details(self, request, *args, **kwargs):
        """
        Associates a case with a a personal details object. Will throw an error
        if the case already has a personal details object associated.
        """

        obj = self.get_object()

        form = AssociatePersonalDetailsCaseForm(case=obj, data=request.DATA)
        if form.is_valid():
            form.save(request.user)
            return DRFResponse(status=status.HTTP_204_NO_CONTENT)
        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )

    @action()
    def associate_thirdparty_details(self, request, *args, **kwargs):

        obj = self.get_object()

        form = AssociateThirdPartyDetailsCaseForm(case=obj, data=request.DATA)
        if form.is_valid():
            form.save(request.user)
            return DRFResponse(status=status.HTTP_204_NO_CONTENT)
        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )

    @action()
    def associate_eligibility_check(self, request, *args, **kwargs):
        """
        Associates a case with a eligibility_check object. Will throw an error
        if the case already has a eligibility_check object associated.
        """

        obj = self.get_object()

        form = AssociateEligibilityCheckCaseForm(case=obj, data=request.DATA)
        if form.is_valid():
            form.save(request.user)
            return DRFResponse(status=status.HTTP_204_NO_CONTENT)
        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )

    @action()
    def associate_adaptation_details(self, request, *args, **kwargs):

        obj = self.get_object()

        form = AssociateAdaptationDetailsCaseForm(case=obj, data=request.DATA)
        if form.is_valid():
            form.save(request.user)
            return DRFResponse(status=status.HTTP_204_NO_CONTENT)
        return DRFResponse(
            dict(form.errors), status=status.HTTP_400_BAD_REQUEST
        )


class ProviderViewSet(CallCentrePermissionsViewSetMixin, viewsets.ReadOnlyModelViewSet):
    model = Provider
    serializer_class = ProviderSerializer

    queryset = Provider.objects.active()

    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('law_category__code',)


class OutOfHoursRotaViewSet(
    CallCentreManagerPermissionsViewSetMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):

    serializer_class = OutOfHoursRotaSerializer
    model = OutOfHoursRota


class UserViewSet(CallCentrePermissionsViewSetMixin, BaseUserViewSet):
    model = Operator
    serializer_class = OperatorSerializer

    def get_logged_in_user_model(self):
        return self.request.user.operator


class PersonalDetailsViewSet(CallCentrePermissionsViewSetMixin,
                             mixins.CreateModelMixin,
                             mixins.UpdateModelMixin,
                             mixins.RetrieveModelMixin,
                             viewsets.GenericViewSet):
    model = PersonalDetails
    serializer_class = PersonalDetailsSerializer
    lookup_field = 'reference'


class EventViewSet(CallCentrePermissionsViewSetMixin, BaseEventViewSet):
    pass


class ThirdPartyDetailsViewSet(CallCentrePermissionsViewSetMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    model = ThirdPartyDetails
    serializer_class = ThirdPartyDetailsSerializer
    lookup_field = 'reference'


class AdaptationDetailsViewSet(CallCentrePermissionsViewSetMixin,
                               mixins.CreateModelMixin,
                               mixins.UpdateModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    model = AdaptationDetails
    serializer_class = AdaptationDetailsSerializer
    lookup_field = 'reference'


class ArticleViewSet(CallCentrePermissionsViewSetMixin, BaseArticleViewSet):
    pass


class ArticleCategoryViewSet(CallCentrePermissionsViewSetMixin,
                             BaseArticleCategoryViewSet):
    pass


class TimerViewSet(CallCentrePermissionsViewSetMixin, BaseTimerViewSet):
    pass
