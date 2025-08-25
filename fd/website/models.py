from django.db import models
from slugify import slugify as slugify_translit


class Advantages(models.Model):
    name = models.CharField('Имя', max_length=200)
    slug = models.SlugField('Слаг', max_length=200, unique=True)
    number = models.PositiveIntegerField('Номер', help_text="Порядковый номер преимущества")
    image = models.ImageField('Изображение', upload_to='advantages/', null=True, blank=True)
    text = models.TextField('Текст', help_text="Описание преимущества")
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return f"{self.number}. {self.name}"

    class Meta:
        verbose_name = "Преимущество"
        verbose_name_plural = "Преимущества"
        ordering = ['number']
        db_table = 'rentals_advantages'
        managed = False


class Blog(models.Model):
    title = models.CharField('Название', max_length=200)
    slug = models.SlugField('Слаг', max_length=200, unique=True, blank=True, null=True)
    category = models.CharField('Категория', max_length=100, null=True, blank=True)
    main_image = models.ImageField('Основное изображение', upload_to='blog/', null=True, blank=True)
    extra_image = models.ImageField('Доп. изображение', upload_to='blog/extra/', null=True, blank=True)
    text = models.TextField('Текст', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return self.title

    def _generate_unique_slug(self):
        base_slug = slugify_translit(self.title or '')
        slug = base_slug or 'blog'
        unique_suffix = 1
        Model = self.__class__
        while Model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            unique_suffix += 1
            slug = f"{base_slug}-{unique_suffix}" if base_slug else f"blog-{unique_suffix}"
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Статья блога'
        verbose_name_plural = 'Статьи блога'
        ordering = ['-created_at']
        db_table = 'rentals_blog'
        managed = False


class Review(models.Model):
    name = models.CharField('Имя', max_length=200)
    slug = models.SlugField('Слаг', max_length=200, unique=True, blank=True, null=True)
    text = models.TextField('Текст')
    image = models.ImageField('Изображение', upload_to='reviews/', null=True, blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return self.name

    def _generate_unique_slug(self):
        base_slug = slugify_translit(self.name or '')
        slug = base_slug or 'review'
        unique_suffix = 1
        Model = self.__class__
        while Model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            unique_suffix += 1
            slug = f"{base_slug}-{unique_suffix}" if base_slug else f"review-{unique_suffix}"
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        db_table = 'rentals_review'
        managed = False


class TransportSale(models.Model):
    name = models.CharField('Название', max_length=255)
    price = models.DecimalField('Цена', max_digits=12, decimal_places=2)
    color = models.CharField('Цвет', max_length=100, blank=True, null=True)

    # Характеристики
    drive = models.CharField('Привод', max_length=100, blank=True, null=True)
    dimensions_l_w_h_mm = models.CharField('Размеры техники ДхШхВ (мм)', max_length=255, blank=True, null=True)
    seat_height_mm = models.CharField('Высота сидения (мм)', max_length=100, blank=True, null=True)
    handlebar_height_mm = models.CharField('Высота по рулю (мм)', max_length=100, blank=True, null=True)
    axle_size_mm = models.CharField('Размер по осям (мм)', max_length=255, blank=True, null=True)
    engine_displacement_cc = models.CharField('Рабочий объем ДВС (сс)', max_length=100, blank=True, null=True)
    engine_power_hp_kw_rpm = models.CharField('Мощность ДВС (л.с/кВт/об.мин)', max_length=255, blank=True, null=True)
    engine_mark_actual = models.CharField('Маркировка ДВС фактически', max_length=255, blank=True, null=True)
    engine_mark_cover = models.CharField('Маркировка ДВС на крышке', max_length=255, blank=True, null=True)
    cooling = models.CharField('Охлаждение', max_length=100, blank=True, null=True)
    start = models.CharField('Запуск', max_length=100, blank=True, null=True)
    fuel_supply = models.CharField('Подача топлива', max_length=100, blank=True, null=True)
    transmission = models.CharField('Трансмиссия', max_length=100, blank=True, null=True)
    gears_count = models.CharField('Количество передач', max_length=100, blank=True, null=True)
    tank_volume_l = models.CharField('Объем бака (л)', max_length=100, blank=True, null=True)
    wheel_front = models.CharField('Колесо переднее', max_length=100, blank=True, null=True)
    wheel_rear = models.CharField('Колесо заднее', max_length=100, blank=True, null=True)
    max_speed_kmh = models.CharField('МАХ скорость (км/час)', max_length=100, blank=True, null=True)
    front_brake_disc = models.CharField('Передний тормозной диск', max_length=100, blank=True, null=True)
    rear_brake_disc = models.CharField('Задний тормозной диск', max_length=100, blank=True, null=True)
    brake_system = models.CharField('Тормозная система', max_length=255, blank=True, null=True)
    optics = models.CharField('Оптика', max_length=255, blank=True, null=True)
    dashboard = models.CharField('Панель приборов', max_length=255, blank=True, null=True)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Продажа транспорта'
        verbose_name_plural = 'Продажа транспорта'
        ordering = ['-created_at']
        db_table = 'rentals_transportsale'
        managed = False


