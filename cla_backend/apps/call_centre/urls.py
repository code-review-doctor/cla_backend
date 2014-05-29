from django.conf.urls import patterns, url, include

from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'category', views.CategoryViewSet)
router.register(r'caselogtype', views.CaseLogTypeViewSet)
router.register(r'provider/rota', views.OutOfHoursRotaViewSet)
router.register(r'outcome_code', views.OutcomeCodeViewSet, base_name='outcome_code')
router.register(r'provider', views.ProviderViewSet)
router.register(r'eligibility_check', views.EligibilityCheckViewSet, base_name='eligibility_check')
router.register(r'case', views.CaseViewSet)
router.register(r'user', views.UserViewSet, base_name='user')

urlpatterns = patterns('',
    url(r'^', include(router.urls)),
)
