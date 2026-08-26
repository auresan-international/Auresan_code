from django.db import models
from django.urls import reverse
from django.conf import settings


class HealthCondition(models.Model):
	slug = models.SlugField(max_length=100, unique=True)
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('website:condition_detail', kwargs={'slug': self.slug})


class Product(models.Model):
	slug = models.SlugField(max_length=120, unique=True)
	title = models.CharField(max_length=200)
	short_description = models.TextField(blank=True)
	benefits = models.TextField(blank=True)
	ingredients = models.TextField(blank=True)
	dosage = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	faqs = models.TextField(blank=True)
	conditions = models.ManyToManyField(HealthCondition, related_name='recommended_products', blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('website:product_detail', kwargs={'slug': self.slug})


class CallbackRequest(models.Model):
	full_name = models.CharField(max_length=200)
	phone_number = models.CharField(max_length=30)
	district = models.CharField(max_length=200, blank=True)
	interest = models.CharField(max_length=200, blank=True)
	best_time = models.CharField(max_length=100, blank=True)
	message = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	source = models.CharField(max_length=100, default='website')
	status = models.CharField(max_length=50, default='new')
	assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

	def __str__(self):
		return f"Callback: {self.full_name} - {self.phone_number}"


class Order(models.Model):
	customer_name = models.CharField(max_length=200)
	phone = models.CharField(max_length=30)
	delivery_address = models.TextField()
	district = models.CharField(max_length=200, blank=True)
	product = models.ForeignKey(Product, on_delete=models.PROTECT)
	quantity = models.PositiveIntegerField(default=1)
	payment_method = models.CharField(max_length=100, blank=True)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"Order #{self.id} - {self.customer_name}"


class Review(models.Model):
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
	author_name = models.CharField(max_length=200)
	rating = models.PositiveSmallIntegerField(default=5)
	text = models.TextField()
	city = models.CharField(max_length=100, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.author_name} - {self.product.title}"


class FAQ(models.Model):
	question = models.CharField(max_length=300)
	answer = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.question


class BlogPost(models.Model):
	slug = models.SlugField(max_length=200, unique=True)
	title = models.CharField(max_length=300)
	excerpt = models.TextField(blank=True)
	body = models.TextField()
	published = models.BooleanField(default=False)
	published_at = models.DateTimeField(null=True, blank=True)

	def __str__(self):
		return self.title

	def get_absolute_url(self):
		return reverse('website:blog_detail', kwargs={'slug': self.slug})

