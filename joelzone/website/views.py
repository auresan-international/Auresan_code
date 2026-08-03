from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from .models import Product, HealthCondition, CallbackRequest, Order, Review, FAQ, BlogPost
from .forms import CallbackRequestForm, OrderForm

User = get_user_model()


def home(request):
    products = Product.objects.all()[:6]
    featured = products[:3]
    return render(request, 'website/home.html', {'products': products, 'featured': featured})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 'website/product_detail.html', {'product': product})


def condition_detail(request, slug):
    condition = get_object_or_404(HealthCondition, slug=slug)
    recommended = condition.recommended_products.all()
    return render(request, 'website/condition_detail.html', {'condition': condition, 'recommended': recommended})


def callback_request(request):
    if request.method == 'POST':
        form = CallbackRequestForm(request.POST)
        if form.is_valid():
            cb = form.save()
            try:
                from customerleads.models import Lead
                fallback_user = User.objects.filter(is_active=True).first()
                if fallback_user:
                    Lead.objects.create(
                        name=cb.full_name,
                        email='',
                        phone=cb.phone_number,
                        company='',
                        status='new',
                        priority='medium',
                        created_by=fallback_user,
                    )
            except Exception:
                pass
            return redirect('website:callback_thanks')
    else:
        form = CallbackRequestForm()
    return render(request, 'website/callback_form.html', {'form': form})


def order_create(request):
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            return redirect('website:order_thanks')
    else:
        form = OrderForm()
    return render(request, 'website/order_form.html', {'form': form})


def contact(request):
    return render(request, 'website/contact.html')


def about(request):
    return render(request, 'website/about.html')


def faqs(request):
    faqs = FAQ.objects.all().order_by('-created_at')
    return render(request, 'website/faqs.html', {'faqs': faqs})


def blog_list(request):
    posts = BlogPost.objects.filter(published=True).order_by('-published_at')
    return render(request, 'website/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, published=True)
    return render(request, 'website/blog_detail.html', {'post': post})
