from django.apps import apps
from django.contrib import admin
from .models import *

# Register all models from this app.
app = apps.get_app_config('customerleads')
for model in app.get_models():
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass


