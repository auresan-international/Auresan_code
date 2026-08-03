from django.urls import path
from django.shortcuts import render
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('condition/<slug:slug>/', views.condition_detail, name='condition_detail'),
    path('callback/', views.callback_request, name='callback'),
    path('callback/thanks/', lambda r: render(r, 'website/callback_thanks.html'), name='callback_thanks'),
    path('order/', views.order_create, name='order_create'),
    path('order/thanks/', lambda r: render(r, 'website/order_thanks.html'), name='order_thanks'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('faqs/', views.faqs, name='faqs'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('products/', views.product_detail, name='product_list'),
]
