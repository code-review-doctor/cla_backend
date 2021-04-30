from django.core.management.base import BaseCommand
from dateutil.relativedelta import relativedelta

from legalaid.models import Case
from cla_butler.tasks import DeleteOldData


class FindAndDeleteCasesUsingCreationTime(DeleteOldData):
    def get_eligible_cases(self):
        two_years = self.now - relativedelta(years=2)

        return Case.objects.filter(created__lte=two_years).exclude(log__created__gte=two_years)


class Command(BaseCommand):
    help = "Find and delete cases that are 2 years old or over that were not deleted prior to the task command being fixed"

    def handle(self, *args, **kwargs):
        FindAndDeleteCasesUsingCreationTime().run()
