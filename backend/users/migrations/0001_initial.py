# Сгенерировано Django 4.2.x 2025-08-09 XX:XX

from django.contrib.auth.models import AbstractUser
from django.db import migrations, models
import django.contrib.auth.validators
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='Пароль')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='Последний вход')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='Суперпользователь')),
                ('username', models.CharField(max_length=150, unique=True, verbose_name='Имя пользователя', validators=[django.contrib.auth.validators.UnicodeUsernameValidator()])),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='Имя')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='Фамилия')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активный')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Дата регистрации')),
                
                # Пользовательские поля FREESPORT
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='Email адрес')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='Номер телефона')),
                ('role', models.CharField(
                    choices=[
                        ('retail', 'Розничный покупатель'),
                        ('wholesale_level1', 'Оптовик уровень 1'),
                        ('wholesale_level2', 'Оптовик уровень 2'),
                        ('wholesale_level3', 'Оптовик уровень 3'),
                        ('trainer', 'Тренер'),
                        ('federation_rep', 'Представитель федерации'),
                        ('admin', 'Администратор'),
                    ],
                    default='retail',
                    max_length=20,
                    verbose_name='Роль пользователя'
                )),
                ('company_name', models.CharField(blank=True, max_length=200, verbose_name='Название компании')),
                ('tax_id', models.CharField(blank=True, max_length=50, verbose_name='ИНН')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Верифицирован')),
                ('verification_token', models.CharField(blank=True, max_length=100, verbose_name='Токен верификации')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
            ],
            options={
                'verbose_name': 'Пользователь',
                'verbose_name_plural': 'Пользователи',
                'db_table': 'freesport_users',
            },
        ),
        
        # Индексы для производительности
        migrations.RunSQL(
            "CREATE INDEX idx_users_email ON freesport_users(email);",
            reverse_sql="DROP INDEX IF EXISTS idx_users_email;"
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_users_role ON freesport_users(role);",
            reverse_sql="DROP INDEX IF EXISTS idx_users_role;"
        ),
    ]