from django.urls import path
from . import views

app_name = 'website'

urlpatterns = [
    path('', views.index, name='index'),
    path('about-us/', views.about_us, name='about_us'),
    path('cars/', views.cars, name='cars'),
    path('categories/', views.categories, name='categories'),
    path('services/', views.services, name='services'),
    path('reviews/', views.reviews, name='reviews'),
    path('blogs/', views.blogs, name='blogs'),
    path('faq/', views.faq, name='faq'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-conditions/', views.terms_conditions, name='terms_conditions'),
    path('cancellation-policy/', views.cancellation_policy, name='cancellation_policy'),
    path('log-in/', views.log_in, name='log_in'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('update-password/', views.update_password, name='update_password'),
    path('user-account/', views.user_account, name='user_account'),
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('access-denied/', views.access_denied, name='access_denied'),

    path('detail/cars/<int:car_id>/', views.car_detail, name='car_detail'),
    path('detail/categories/<int:category_id>/', views.category_detail, name='category_detail'),
    path('detail/services/<int:service_id>/', views.service_detail, name='service_detail'),
    path('detail/reviews/<int:review_id>/', views.review_detail, name='review_detail'),
    path('detail/blog-posts/<int:blog_id>/', views.blog_detail, name='blog_detail'),
]
