from django import forms
from .models import CallbackRequest, Order


class CallbackRequestForm(forms.ModelForm):
    class Meta:
        model = CallbackRequest
        fields = ['full_name', 'phone_number', 'district', 'interest', 'best_time', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer_name', 'phone', 'delivery_address', 'district', 'product', 'quantity', 'payment_method', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
