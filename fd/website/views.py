from django.shortcuts import render
from rentals.models import Transport


def index(request):
    transports = Transport.objects.all().order_by('number', 'name')[:12]
    return render(request, 'website/index.html', {
        'transports': transports,
    })


def about_us(request):
    return render(request, 'website/about-us.html')


def cars(request):
    return render(request, 'website/cars.html')


def categories(request):
    return render(request, 'website/categories.html')


def services(request):
    return render(request, 'website/services.html')


def reviews(request):
    return render(request, 'website/reviews.html')


def blogs(request):
    return render(request, 'website/blogs.html')


def faq(request):
    return render(request, 'website/faq.html')


def contact_us(request):
    return render(request, 'website/contact-us.html')


def privacy_policy(request):
    return render(request, 'website/privacy-policy.html')


def terms_conditions(request):
    return render(request, 'website/terms-conditions.html')


def cancellation_policy(request):
    return render(request, 'website/cancellation-policy.html')


def log_in(request):
    return render(request, 'website/log-in.html')


def sign_up(request):
    return render(request, 'website/sign-up.html')


def reset_password(request):
    return render(request, 'website/reset-password.html')


def update_password(request):
    return render(request, 'website/update-password.html')


def user_account(request):
    return render(request, 'website/user-account.html')


def coming_soon(request):
    return render(request, 'website/coming-soon.html')


def access_denied(request):
    return render(request, 'website/access-denied.html')


def car_detail(request, car_id):
    return render(request, 'website/detail_cars.html', {'car_id': car_id})


def category_detail(request, category_id):
    return render(request, 'website/detail_categories.html', {'category_id': category_id})


def service_detail(request, service_id):
    return render(request, 'website/detail_services.html', {'service_id': service_id})


def review_detail(request, review_id):
    return render(request, 'website/detail_reviews.html', {'review_id': review_id})


def blog_detail(request, blog_id):
    return render(request, 'website/detail_blog-posts.html', {'blog_id': blog_id})
