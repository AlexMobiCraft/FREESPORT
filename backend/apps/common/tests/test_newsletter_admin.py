"""
Действия рассылки в списках новостей и статей: `/marketing/` (маркетинг и
руководитель) и `/admin/` (суперпользователь), колонка «Рассылка» и запись
в журнале руководителя.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from apps.common import tasks
from apps.common.admin import ALREADY_SENT_MESSAGE, ONE_ARTICLE_MESSAGE, QUEUE_DOWN_MESSAGE, TEST_FAILED_MESSAGE
from apps.common.models import AuditLog, BlogPost, News, NewsletterCampaign, NewsletterDelivery
from apps.common.services.marketing_email import (
    STATUS_MAILBOX_FAILED,
    TEST_EMAIL_NOTICE,
    SmtpMarketingTransport,
    TransportResult,
)
from apps.common.services.newsletter_campaign import CAP_REACHED_MESSAGE, NOT_PUBLISHED_MESSAGE
from apps.common.tests.test_newsletter_campaign import (  # noqa: F401 — autouse-фикстура настроек
    make_news,
    make_post,
    set_sent,
    site_settings,
    subscribers,
)
from apps.users.models import User
from apps.users.staff_roles import MANAGERS_GROUP, MARKETING_GROUP, SUPERVISORS_GROUP
from tests.conftest import get_unique_suffix
from tests.integration.test_manager_clients_section import (  # noqa: F401 — autouse-фикстура групп
    PASSWORD,
    make_staff_member,
    role_groups,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

NEWS_URL = "/marketing/common/news/"
BLOG_URL = "/marketing/common/blogpost/"
ADMIN_NEWS_URL = "/admin/common/news/"
JOURNAL_URL = "/supervisor/journal/"
DELAY = "apps.common.tasks.send_newsletter_campaign.delay"


def logged_in(user: User) -> Client:
    browser = Client()
    browser.force_login(user)
    return browser


def action(browser: Client, url: str, name: str, *articles: Any, confirm: bool = False, **extra: Any):
    data: dict[str, Any] = {"action": name, "_selected_action": [str(a.pk) for a in articles]}
    if confirm:
        data["post"] = "yes"
    return browser.post(url, data, follow=True, **extra)


def texts(response) -> list[str]:
    return [str(message) for message in response.context["messages"]]


@pytest.fixture
def marketer() -> User:
    return make_staff_member(MARKETING_GROUP)


@pytest.fixture
def as_marketer(marketer) -> Client:
    return logged_in(marketer)


class TestActionsAndRights:
    @pytest.mark.parametrize("group", [MARKETING_GROUP, SUPERVISORS_GROUP])
    @pytest.mark.parametrize("url", [NEWS_URL, BLOG_URL])
    def test_section_roles_see_both_actions(self, group, url):
        response = logged_in(make_staff_member(group)).get(url)

        choices = dict(response.context["action_form"].fields["action"].choices)
        assert choices["send_newsletter"] == "Разослать подписчикам"
        assert choices["send_newsletter_test"] == "Отправить тест мне"

    def test_superuser_in_admin(self):
        superuser = User.objects.create_superuser(email=f"su_{get_unique_suffix()}@example.com", password=PASSWORD)
        news = make_news()
        subscribers(2)

        response = action(logged_in(superuser), ADMIN_NEWS_URL, "send_newsletter", news)

        assert response.status_code == 200
        assert "Отправить 2 подписчикам?" in response.content.decode()

    def test_view_only_has_no_actions_and_cannot_post(self, as_marketer):
        group = Group.objects.get(name=MARKETING_GROUP)
        group.permissions.set(Permission.objects.filter(codename__in=["view_news", "view_blogpost"]))
        news = make_news()
        subscribers(1)

        response = as_marketer.get(NEWS_URL)
        assert response.context["action_form"] is None

        with patch(DELAY) as delay:
            action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)
        delay.assert_not_called()
        assert not NewsletterCampaign.objects.exists()

    def test_manager_has_no_access(self):
        news = make_news()
        browser = logged_in(make_staff_member(MANAGERS_GROUP))

        response = browser.post(NEWS_URL, {"action": "send_newsletter", "_selected_action": [str(news.pk)]})

        assert response.status_code == 302 and "/marketing/login/" in response["Location"]
        assert not NewsletterCampaign.objects.exists()


class TestConfirmation:
    def test_page_shows_count_and_daily_limit_without_creating(self, as_marketer, settings):
        settings.NEWSLETTER_DAILY_CAP = 10
        set_sent(4)
        news = make_news()
        subscribers(3)

        response = action(as_marketer, NEWS_URL, "send_newsletter", news)

        assert response.status_code == 200
        assert response.templates[0].name == "admin/common/newsletter_send_confirmation.html"
        html = response.content.decode()
        assert "Отправить 3 подписчикам?" in html
        assert "За сутки уйдёт не больше 6" in html
        assert "Остаток останется в очереди" not in html
        assert news.title in html
        assert 'name="post" value="yes"' in html
        assert f'name="_selected_action" value="{news.pk}"' in html
        assert 'name="action" value="send_newsletter"' in html
        assert f'href="{NEWS_URL}"' in html  # «Отмена» и крошки — в разделе маркетинга
        assert 'href="/admin/' not in html
        assert not NewsletterCampaign.objects.filter(news=news).exists()

    def test_page_mentions_remainder_only_above_quota(self, as_marketer, settings):
        settings.NEWSLETTER_DAILY_CAP = 2
        news = make_news()
        subscribers(3)

        html = action(as_marketer, NEWS_URL, "send_newsletter", news).content.decode()

        assert "Отправить 3 подписчикам?" in html
        assert "За сутки уйдёт не больше 2" in html
        assert "Остаток останется в очереди" in html

    def test_cancel_sends_nothing(self, as_marketer):
        news = make_news()
        subscribers(2)

        with patch(DELAY) as delay:
            action(as_marketer, NEWS_URL, "send_newsletter", news)
            response = as_marketer.get(NEWS_URL)  # «Отмена» — ссылка на список

        assert response.status_code == 200
        delay.assert_not_called()
        assert not NewsletterCampaign.objects.exists()
        assert mail.outbox == []

    def test_confirm_starts_campaign_and_journal(self, as_marketer, marketer):
        news = make_news()
        readers = subscribers(3)

        with patch(DELAY, side_effect=lambda campaign_id: tasks.send_newsletter_campaign(campaign_id)) as delay:
            response = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)

        campaign = NewsletterCampaign.objects.get(news=news)
        delay.assert_called_once_with(campaign.pk)
        assert any("Рассылка запущена" in text and "получателей — 3" in text for text in texts(response))
        assert not any("остаток" in text for text in texts(response))
        assert sorted(email.to[0] for email in mail.outbox) == sorted(r.email for r in readers)
        for email in mail.outbox:
            assert "List-Unsubscribe" in email.extra_headers and "List-Unsubscribe-Post" in email.extra_headers
            assert f"/news/{news.slug}" in email.body
        entry = AuditLog.objects.get(action="newsletter_send")
        assert (entry.user, entry.resource_type, entry.resource_id) == (marketer, "News", str(news.pk))

        listing = as_marketer.get(NEWS_URL).content.decode()
        assert "отправлено 3 · ошибок 0 · в очереди 0" in listing

    def test_more_than_one_selected_is_refused(self, as_marketer):
        first, second = make_news(), make_news()
        subscribers(1)

        with patch(DELAY) as delay:
            response = action(as_marketer, NEWS_URL, "send_newsletter", first, second)
            confirmed = action(as_marketer, NEWS_URL, "send_newsletter", first, second, confirm=True)

        assert ONE_ARTICLE_MESSAGE in texts(response)
        assert ONE_ARTICLE_MESSAGE in texts(confirmed)
        delay.assert_not_called()
        assert not NewsletterCampaign.objects.exists()

    @pytest.mark.parametrize("confirm", [False, True])
    def test_unpublished_is_refused(self, as_marketer, confirm):
        news = make_news(is_published=False)
        subscribers(1)

        with patch(DELAY) as delay:
            response = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=confirm)

        assert NOT_PUBLISHED_MESSAGE in texts(response)
        delay.assert_not_called()
        assert not NewsletterCampaign.objects.exists()

    def test_queue_down_keeps_rows_pending(self, as_marketer):
        news = make_news()
        subscribers(2)

        with patch(DELAY, side_effect=ConnectionError("redis down")):
            response = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)

        assert QUEUE_DOWN_MESSAGE in texts(response)
        campaign = NewsletterCampaign.objects.get(news=news)
        assert list(campaign.deliveries.values_list("status", flat=True)) == ["pending", "pending"]
        assert mail.outbox == []
        assert not AuditLog.objects.filter(action="newsletter_send").exists()

    def test_success_mentions_remainder_above_quota(self, as_marketer, settings):
        settings.NEWSLETTER_DAILY_CAP = 2
        news = make_news()
        subscribers(3)

        with patch(DELAY):
            response = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)

        assert any("получателей — 3" in text and "За сутки уйдёт не больше 2 писем" in text for text in texts(response))

    @pytest.mark.parametrize("confirm", [False, True])
    def test_cap_exhausted_is_refused(self, as_marketer, settings, confirm):
        settings.NEWSLETTER_DAILY_CAP = 1
        set_sent(1)
        news = make_news()
        subscribers(1)

        with patch(DELAY) as delay:
            response = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=confirm)

        assert CAP_REACHED_MESSAGE in texts(response)
        delay.assert_not_called()
        assert not NewsletterCampaign.objects.filter(news=news).exists()

    def test_already_sent_to_all(self, as_marketer):
        news = make_news()
        subscribers(1)
        with patch(DELAY, side_effect=lambda campaign_id: tasks.send_newsletter_campaign(campaign_id)):
            action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)
        mail.outbox.clear()

        with patch(DELAY) as delay:
            response = action(as_marketer, NEWS_URL, "send_newsletter", news)
            confirmed = action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)

        assert ALREADY_SENT_MESSAGE in texts(response)
        assert ALREADY_SENT_MESSAGE in texts(confirmed)
        delay.assert_not_called()
        assert mail.outbox == []

    def test_blog_post_by_supervisor(self):
        supervisor = make_staff_member(SUPERVISORS_GROUP)
        post = make_post()
        subscribers(1)

        with patch(DELAY) as delay:
            response = action(logged_in(supervisor), BLOG_URL, "send_newsletter", post, confirm=True)

        campaign = NewsletterCampaign.objects.get(blog_post=post)
        delay.assert_called_once_with(campaign.pk)
        assert any("Статья блога" in text for text in texts(response))


class TestTestLetter:
    def test_goes_to_staff_only(self, as_marketer, marketer):
        news = make_news()
        subscribers(3)

        response = action(as_marketer, NEWS_URL, "send_newsletter_test", news)

        assert f"Тестовое письмо отправлено на {marketer.email}." in texts(response)
        assert [email.to for email in mail.outbox] == [[marketer.email]]
        assert "List-Unsubscribe" not in mail.outbox[0].extra_headers
        assert mail.outbox[0].body.startswith(TEST_EMAIL_NOTICE)
        assert not NewsletterCampaign.objects.exists() and not NewsletterDelivery.objects.exists()

    @pytest.mark.parametrize("status", ["failed", STATUS_MAILBOX_FAILED])
    def test_transport_failure_shows_error(self, as_marketer, status):
        news = make_news()
        failure = TransportResult(status=status, error="SMTPDataError: (554, b'5.7.1 rejected')")

        with patch.object(SmtpMarketingTransport, "send", return_value=failure):
            response = action(as_marketer, NEWS_URL, "send_newsletter_test", news)

        assert TEST_FAILED_MESSAGE in texts(response)
        assert not any("Тестовое письмо отправлено" in text for text in texts(response))
        assert mail.outbox == []
        assert not NewsletterCampaign.objects.exists()

    def test_more_than_one_selected_is_refused(self, as_marketer):
        response = action(as_marketer, NEWS_URL, "send_newsletter_test", make_news(), make_news())

        assert ONE_ARTICLE_MESSAGE in texts(response)
        assert mail.outbox == []

    def test_staff_without_email(self):
        member = make_staff_member(MARKETING_GROUP)
        User.objects.filter(pk=member.pk).update(email="")
        member.refresh_from_db()

        response = action(logged_in(member), NEWS_URL, "send_newsletter_test", make_news())

        assert any("не указан email" in text for text in texts(response))
        assert mail.outbox == []


class TestColumn:
    def test_counters_and_dash(self, as_marketer):
        sent_news, fresh_news = make_news(), make_news()
        a, b, c, d = subscribers(4)
        campaign = NewsletterCampaign.objects.create(news=sent_news)
        for subscription, status in ((a, "sent"), (b, "failed"), (c, "pending"), (d, "sending")):
            NewsletterDelivery.objects.create(campaign=campaign, newsletter=subscription, status=status)

        response = as_marketer.get(NEWS_URL)

        rows = {
            obj.pk: response.context["cl"].model_admin.newsletter_status(obj)
            for obj in response.context["cl"].result_list
        }
        assert rows[sent_news.pk] == "отправлено 1 · ошибок 1 · в очереди 2"
        assert rows[fresh_news.pk] == "—"
        assert "Рассылка" in response.content.decode()

    def test_column_does_not_add_queries_per_row(self, as_marketer):
        def add(count: int) -> None:
            for _ in range(count):
                news = make_news()
                campaign = NewsletterCampaign.objects.create(news=news)
                NewsletterDelivery.objects.create(campaign=campaign, newsletter=subscribers(1)[0], status="sent")

        add(2)
        with CaptureQueriesContext(connection) as first:
            assert as_marketer.get(NEWS_URL).status_code == 200
        add(5)
        with CaptureQueriesContext(connection) as second:
            assert as_marketer.get(NEWS_URL).status_code == 200

        assert len(second) == len(first)

    def test_news_with_campaign_can_be_deleted(self, as_marketer):
        news = make_news()
        subscribers(1)
        with patch(DELAY):
            action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)

        response = action(as_marketer, NEWS_URL, "delete_selected", news, confirm=True)

        assert response.status_code == 200
        assert not News.objects.filter(pk=news.pk).exists()
        assert not NewsletterCampaign.objects.exists()
        # Строки доставки остаются для суточного потолка (SET_NULL).
        assert NewsletterDelivery.objects.filter(campaign__isnull=True).count() == 1


class TestJournal:
    def test_supervisor_sees_mailing_with_article(self, as_marketer, marketer):
        post = make_post()
        subscribers(2)
        with patch(DELAY):
            action(as_marketer, BLOG_URL, "send_newsletter", post, confirm=True)

        html = logged_in(make_staff_member(SUPERVISORS_GROUP)).get(JOURNAL_URL).content.decode()

        assert "Рассылка подписчикам" in html
        assert f"Статья блога «{post.title}»" in html
        assert "получателей: 2" in html
        assert f'href="{BLOG_URL}{post.pk}/change/"' in html

    def test_deleted_article_has_no_link(self, as_marketer):
        news = make_news()
        subscribers(1)
        with patch(DELAY):
            action(as_marketer, NEWS_URL, "send_newsletter", news, confirm=True)
        title, pk = news.title, news.pk
        news.delete()

        html = logged_in(make_staff_member(SUPERVISORS_GROUP)).get(JOURNAL_URL).content.decode()

        assert f"Новость «{title}»" in html
        assert f"{NEWS_URL}{pk}/change/" not in html
