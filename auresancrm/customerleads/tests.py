from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class OperatorDashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='operator',
            password='pass12345',
            first_name='Op',
            last_name='Tester',
        )
        self.client.force_login(self.user)

    def test_operator_dashboard_includes_chart_data(self):
        response = self.client.get(reverse('staff_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('chart_data', response.context)
        self.assertEqual(response.context['chart_data']['labels'][0], 'Time in calls')

    def test_charts_view_renders_chart_data(self):
        response = self.client.get(reverse('staff_charts'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('chart_data', response.context)
